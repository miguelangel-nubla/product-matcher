"""
Product matching service using token overlap and fuzzy string matching.
"""

import json
import time
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlmodel import Session

from app.adapters.base import ProductDatabaseAdapter
from app.config.loader import get_global_settings
from app.services.normalization import normalize_text


@dataclass
class DebugStep:
    """Represents a single debug step."""

    message: str
    timestamp: float
    data: str | None = None


@dataclass
class MatchingDebugInfo:
    """Complete debug information for a matching operation."""

    steps: list[DebugStep]
    start_time: float

    def to_strings(self) -> list[str]:
        """Convert to list of formatted strings."""
        if not self.steps:
            return []

        result = []
        for i, step in enumerate(self.steps):
            total_ms = (step.timestamp - self.start_time) * 1000
            if i == 0:
                step_ms = total_ms
            else:
                step_ms = (step.timestamp - self.steps[i - 1].timestamp) * 1000

            result.append(f"[{total_ms:.0f}ms +{step_ms:.0f}ms] {step.message}")

        return result

    @property
    def total_duration_ms(self) -> float:
        """Calculate total duration in milliseconds."""
        if not self.steps:
            return 0.0
        return (self.steps[-1].timestamp - self.start_time) * 1000


class DebugStepTracker:
    """Tracks debug steps with timing information."""

    def __init__(self) -> None:
        self.steps: list[DebugStep] = []
        self.start_time = time.time()

    def add(self, message: str, data: str | None = None) -> None:
        """Add a debug step."""
        step = DebugStep(message=message, timestamp=time.time(), data=data)
        self.steps.append(step)

    def get_debug_info(self) -> MatchingDebugInfo:
        """Get complete debug information."""
        return MatchingDebugInfo(steps=self.steps, start_time=self.start_time)


# Static threshold for token overlap - very restrictive to ensure high confidence
TOKEN_OVERLAP_THRESHOLD = 0.8
# Minimum number of tokens required to attempt Jaccard similarity
MIN_TOKENS_FOR_JACCARD = 2


def calculate_jaccard_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """
    Calculate Jaccard similarity (token overlap) between two token lists.

    Args:
        tokens1: First set of tokens
        tokens2: Second set of tokens

    Returns:
        Jaccard similarity score (0.0 to 1.0)
    """
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0

    set1 = set(tokens1)
    set2 = set(tokens2)

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


class ProductMatcher:
    """
    Main product matching service that handles fuzzy matching
    of normalized text against live external product data.
    """

    def __init__(self, session: Session, adapter: ProductDatabaseAdapter):
        self.session = session
        self.adapter = adapter

    def match_product(
        self, text: str, backend_name: str, threshold: float | None = None
    ) -> tuple[bool, str, list[tuple[str, float]], MatchingDebugInfo]:
        """
        Main matching function using token overlap and fuzzy fallback.

        Algorithm:
        1. Normalize input text to tokens
        2. If input has >= MIN_TOKENS_FOR_JACCARD:
           a. Calculate Jaccard for all aliases
           b. If exactly one alias passes TOKEN_OVERLAP_THRESHOLD: return it
        3. Fallback to fuzzy matching for all aliases
        4. Return best fuzzy matches above threshold

        Args:
            text: Original input text
            backend_name: Backend instance name to get language configuration
            threshold: Minimum confidence threshold for fuzzy matching

        Returns:
            Tuple: (success, normalized_input, candidates, debug_info)
        """
        # Initialize debug tracker
        debug = DebugStepTracker()

        # Load global settings and apply defaults
        global_settings = get_global_settings()
        if threshold is None:
            threshold = global_settings.get("default_threshold", 0.8)
        max_candidates = global_settings.get("max_candidates", 5)

        debug.add(f"Using threshold: {threshold}, max_candidates: {max_candidates}")

        # Get language and configuration from backend
        from app.adapters.registry import get_backend_language
        from app.config.loader import get_backend_config

        language = get_backend_language(backend_name)
        backend_config = get_backend_config(backend_name)
        debug.add(f"Original input: '{text}' (language: {language})")

        # Normalize the input text to tokens using backend configuration
        input_tokens = normalize_text(text, language, backend_config)
        debug.add(f"After normalization: {input_tokens}")

        # For display purposes, join tokens back to normalized string
        normalized_input = " ".join(input_tokens)

        # Get all products live from external system
        try:
            products = self.adapter.get_all_products()
            debug.add(f"Loaded {len(products)} products from backend")
        except Exception as e:
            # Re-raise adapter errors so they can be handled by the API layer
            raise RuntimeError(f"Backend adapter error: {e}")

        if not products:
            debug.add("No products found, returning empty result")
            return False, normalized_input, [], debug.get_debug_info()

        # Step 1: Try Jaccard similarity if input has enough tokens
        if len(input_tokens) >= MIN_TOKENS_FOR_JACCARD:
            debug.add(
                f"Input has {len(input_tokens)} tokens (>= {MIN_TOKENS_FOR_JACCARD}), attempting Jaccard matching"
            )
            jaccard_product_scores: dict[
                str, tuple[str, float]
            ] = {}  # Track best score per product
            jaccard_candidates_checked = 0

            for product in products:
                for alias in product.aliases:
                    alias_tokens = normalize_text(alias, language, backend_config)

                    # Only attempt Jaccard if alias also has enough tokens
                    if len(alias_tokens) >= MIN_TOKENS_FOR_JACCARD:
                        jaccard_candidates_checked += 1
                        overlap_score = calculate_jaccard_similarity(
                            input_tokens, alias_tokens
                        )

                        if overlap_score >= TOKEN_OVERLAP_THRESHOLD:
                            debug.add(
                                f"  Jaccard match found: '{alias}' -> {alias_tokens} (score: {overlap_score:.3f})"
                            )

                            # Track best score for this product (multiple aliases of same product is fine)
                            if (
                                product.id not in jaccard_product_scores
                                or overlap_score > jaccard_product_scores[product.id][1]
                            ):
                                jaccard_product_scores[product.id] = (
                                    alias,
                                    overlap_score,
                                )

            debug.add(
                f"Checked {jaccard_candidates_checked} aliases for Jaccard, found {len(jaccard_product_scores)} unique products with matches"
            )

            # If exactly one PRODUCT passes Jaccard threshold, return it (high confidence)
            if len(jaccard_product_scores) == 1:
                product_id, (best_alias, best_score) = list(
                    jaccard_product_scores.items()
                )[0]
                debug.add(
                    f"Exactly 1 product matched via Jaccard ('{best_alias}' score: {best_score:.3f}) - returning high confidence result"
                )
                jaccard_matches = [(product_id, best_score)]
                return True, normalized_input, jaccard_matches, debug.get_debug_info()
            elif len(jaccard_product_scores) > 1:
                debug.add(
                    f"Multiple products matched via Jaccard ({len(jaccard_product_scores)} products), falling back to fuzzy matching"
                )
            else:
                debug.add(
                    "No products matched via Jaccard, falling back to fuzzy matching"
                )
        else:
            debug.add(
                f"Input has only {len(input_tokens)} tokens (< {MIN_TOKENS_FOR_JACCARD}), skipping Jaccard, using fuzzy matching"
            )

        # Step 2: Fallback to fuzzy matching for all aliases
        debug.add(f"Starting fuzzy matching with threshold {threshold}")

        # Step 2a: Extract all product->aliases mappings
        total_aliases = sum(len(product.aliases) for product in products)
        debug.add(
            f"Extracted {total_aliases} aliases from {len(products)} products for fuzzy matching"
        )

        # Step 2b: Normalize all aliases with detailed phase tracking
        debug.add(f"Starting detailed normalization of {total_aliases} aliases")

        # Get language module from language argument
        try:
            lang_module = __import__(
                f"app.services.normalization.{language}", fromlist=[language]
            )
        except ImportError:
            raise RuntimeError(
                f"Normalization module for language '{language}' not found"
            )

        # Phase 1: Fast normalization
        debug.add(
            f"Fast normalization (case, accents, punctuation) of {total_aliases} aliases"
        )
        aliases_data = []
        for product in products:
            for alias in product.aliases:
                fast_normalized = lang_module.fast_normalize(alias)
                aliases_data.append((product.id, alias, fast_normalized))
        # Show examples: original -> fast normalized
        examples = [(orig, fast) for _, orig, fast in aliases_data[:3]]
        debug.add("Fast normalization examples", json.dumps(examples, indent=2))

        # Phase 2: SpaCy tokenization
        debug.add(f"SpaCy tokenization of {len(aliases_data)} aliases")
        tokenization_input = [
            (aliases_data[i][2]) for i in range(min(3, len(aliases_data)))
        ]  # Store fast_normalized for examples
        for i, (product_id, original_alias, fast_normalized) in enumerate(aliases_data):
            doc = lang_module.tokenize_text(fast_normalized)
            aliases_data[i] = (product_id, original_alias, doc)
        # Show examples: fast_normalized -> tokens
        token_examples = [
            (tokenization_input[i], [token.text for token in aliases_data[i][2]])
            for i in range(min(3, len(aliases_data)))
        ]
        debug.add("Tokenization examples", json.dumps(token_examples, indent=2))

        # Phase 3: SpaCy lemmatization
        debug.add(f"SpaCy lemmatization of {len(aliases_data)} aliases")
        lemmatization_input = [
            ([token.text for token in aliases_data[i][2]])
            for i in range(min(3, len(aliases_data)))
        ]  # Store tokens for examples
        for i, (product_id, original_alias, doc) in enumerate(aliases_data):
            lemmatized_tokens = lang_module.lemmatize_tokens(doc)
            aliases_data[i] = (product_id, original_alias, lemmatized_tokens)
        # Show examples: tokens -> lemmatized tokens
        lemma_examples = [
            (lemmatization_input[i], aliases_data[i][2])
            for i in range(min(3, len(aliases_data)))
        ]
        debug.add("Lemmatization examples", json.dumps(lemma_examples, indent=2))

        # Phase 4: Post-processing
        debug.add(
            f"Post-processing (abbreviations, stopwords) of {len(aliases_data)} aliases"
        )
        postprocessing_input = [
            (aliases_data[i][2]) for i in range(min(3, len(aliases_data)))
        ]  # Store lemmatized tokens for examples
        normalized_aliases = []
        for product_id, original_alias, lemmatized_tokens in aliases_data:
            final_tokens = lang_module.post_process_tokens(lemmatized_tokens)
            normalized_aliases.append((product_id, original_alias, final_tokens))
        # Show examples: lemmatized tokens -> final tokens
        final_examples = [
            (postprocessing_input[i], normalized_aliases[i][2])
            for i in range(min(3, len(normalized_aliases)))
        ]
        debug.add("Post-processing examples", json.dumps(final_examples, indent=2))

        # Step 2c: Perform fuzzy matching against all normalized aliases
        debug.add(
            f"Computing fuzzy scores against {len(normalized_aliases)} normalized aliases"
        )
        scored_matches = []
        input_text = " ".join(input_tokens)

        # Store all fuzzy calculations for examples
        all_fuzzy_scores = []
        product_best_scores: dict[
            str, tuple[str, float, list[str]]
        ] = {}  # Track best score per product
        for product_id, original_alias, alias_tokens in normalized_aliases:
            alias_text = " ".join(alias_tokens)

            if input_text and alias_text:
                fuzzy_score = fuzz.ratio(input_text, alias_text) / 100.0
                all_fuzzy_scores.append(
                    (input_text, alias_text, fuzzy_score, original_alias, product_id)
                )

                # Track best score for this product
                if (
                    product_id not in product_best_scores
                    or fuzzy_score > product_best_scores[product_id][1]
                ):
                    product_best_scores[product_id] = (
                        original_alias,
                        fuzzy_score,
                        alias_tokens,
                    )

        # Show examples of fuzzy matching calculations
        fuzzy_examples = [
            {
                "query": query,
                "normalized_alias": alias,
                "score": round(score, 3),
                "original_alias": orig,
                "product_id": pid,
            }
            for query, alias, score, orig, pid in all_fuzzy_scores[:max_candidates]
        ]
        debug.add("Fuzzy matching examples", json.dumps(fuzzy_examples, indent=2))

        # Collect products that meet threshold
        for product_id, (_, best_score, _) in product_best_scores.items():
            if best_score >= threshold:
                scored_matches.append((product_id, best_score))

        debug.add(
            f"Found {len(scored_matches)} products above threshold {threshold} from {len(normalized_aliases)} aliases"
        )

        # Sort by score (descending) and take top candidates
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_matches[:max_candidates]

        # Check for ambiguous matches (multiple products with same top score)
        if len(top_candidates) > 1:
            top_score = top_candidates[0][1]
            top_score_count = sum(
                1 for _, score in top_candidates if score == top_score
            )
            if top_score_count > 1:
                debug.add(
                    f"Found {top_score_count} products with identical top score {top_score:.3f} - treating as no match due to ambiguity"
                )
                success = False
            else:
                debug.add(f"Single best match found with score {top_score:.3f}")
                success = True
        elif len(top_candidates) == 1:
            debug.add(f"Single match found with score {top_candidates[0][1]:.3f}")
            success = True
        else:
            debug.add("No matches found above threshold")
            success = False

        debug.add(
            f"Returning top {len(top_candidates)} candidates (success: {success})"
        )

        return success, normalized_input, top_candidates, debug.get_debug_info()

    def add_learned_alias(
        self, external_product_id: str, alias: str
    ) -> tuple[bool, str | None]:
        """
        Add a learned alias to the external system.

        Args:
            external_product_id: ID of the product in external system
            alias: New alias to add

        Returns:
            Tuple of (success boolean, error message if any)
        """
        return self.adapter.add_alias(external_product_id, alias)

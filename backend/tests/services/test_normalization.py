"""
Tests for text normalization.
"""

import pytest

from app.services.normalization.es import SpanishNormalizer, post_process_tokens
from app.services.normalization.registry import get_normalizer, registry


class TestNormalization:
    """Test normalization functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Register Spanish normalizer for testing
        self.normalizer = SpanishNormalizer(config={})
        registry.register("es", self.normalizer)

    def test_normalize_text_english(self):
        """Test basic English normalization."""
        from app.services.normalization.en import EnglishNormalizer

        en_normalizer = EnglishNormalizer(config={})
        result = en_normalizer.normalize("Organic Gala Apples 2pkg")
        assert isinstance(result, list)
        # "2" number stripped, "pkg" expanded to "package" which is in STOPWORDS so removed
        # "organic" is in STOPWORDS so removed
        # "apple" lemma should be present
        assert "apple" in result or "apples" in result
        assert "gala" in result

        # Test multi-word expansions (e.g. xl -> extra large -> both are stopwords and removed)
        res_xl = en_normalizer.normalize("Gala Apples xl")
        assert "extra large" not in res_xl
        assert "gala" in res_xl

        # Test slash expansions (w/ -> with -> stopword; w/o -> without)
        res_w = en_normalizer.normalize("Coffee w/ Milk")
        assert "coffee" in res_w
        assert "milk" in res_w
        assert "w" not in res_w

        res_wo = en_normalizer.normalize("Coffee w/o Milk")
        assert "without" in res_wo
        assert "coffee" in res_wo
        assert "milk" in res_wo


    def test_normalize_text_spanish_basic(self):
        """Test basic Spanish normalization."""
        try:
            result = self.normalizer.normalize("Jugo de Manzana")
            assert isinstance(result, list)
            # "de" is stopword, "Jugo" -> "jugo" (lemma), "Manzana" -> "manzana"
            assert "jugo" in result
            assert "manzana" in result
            assert "de" not in result
        except RuntimeError:
            pytest.skip("SpaCy model not available")

    def test_normalize_text_empty(self):
        """Test normalization with empty input."""
        result = self.normalizer.normalize("")
        assert result == []

    def test_normalize_text_whitespace(self):
        """Test normalization with only whitespace."""
        result = self.normalizer.normalize("   ")
        assert result == []

    def test_normalize_text_unknown_language(self):
        """Test normalization with unknown language."""
        with pytest.raises(ValueError, match="No normalizer registered"):
            get_normalizer("xx")

    def test_normalize_stopwords_with_accents(self):
        """Test normalization removes stopwords even if input has accents."""
        try:
            # "rápido" -> "rapido" (stopword), "fácil" -> "facil" (stopword)
            result = self.normalizer.normalize("coches rápido fácil automático")
            assert "rapido" not in result
            assert "facil" not in result
            assert "automatico" not in result
            # "coches" -> "coche" (lemma) or keep "coches" if lemma fails locally
            assert "coche" in result or "coches" in result
        except RuntimeError:
             pytest.skip("SpaCy model not available")

    def test_post_process_roman_numerals(self):
        """Test removal of roman numerals."""
        tokens = ["carlos", "iii", "juan", "iv", "siglo", "xx"]
        processed = post_process_tokens(tokens)
        assert "iii" not in processed
        assert "iv" not in processed
        # "xx" might be considered roman numeral for 20? Yes.
        assert "xx" not in processed
        assert "carlos" in processed
        assert "juan" in processed

    def test_post_process_split_numbers(self):
        """Test splitting and removal of numbers."""
        # "750ml" -> "750", "ml" -> "ml" -> "mililitro" -> REMOVED (stopword)
        # We test with a non-stopword suffix to verify splitting logic
        tokens = ["botella", "750xyz", "2abc"]
        processed = post_process_tokens(tokens, stopwords=set(), expansions={})
        # 750 removed, 2 removed
        # xyz kept, abc kept
        assert "750" not in processed
        assert "2" not in processed
        assert "xyz" in processed
        assert "abc" in processed
        assert "botella" in processed

    def test_post_process_abbreviations(self):
        """Test abbreviation expansion."""
        # Use custom expansions where result is NOT a stopword
        expansions = {"tst": "testtoken"}
        tokens = ["tst", "other"]
        processed = post_process_tokens(tokens, expansions=expansions, stopwords=set())
        assert "testtoken" in processed
        assert "other" in processed

    def test_normalize_with_custom_config(self):
        """Test normalization with custom configuration."""
        custom_config = {
            "stopwords": ["manzana"], # treat manzana as stopword
            "expansions": {"jug": "jugo"}
        }
        # Create a new normalizer with custom config
        norm = SpanishNormalizer(config=custom_config)

        # Test custom stopword via public API if possible, but easier to unit test post_process
        tokens = ["manzana", "jug"]

        # Note: SpanishNormalizer.normalize() calls post_process with its instance config.
        # But here we want to test that the instance config was correctly loaded.
        assert "manzana" in norm.custom_stopwords
        assert norm.custom_expansions["jug"] == "jugo"

        # Apply using the loaded config

        processed = post_process_tokens(tokens, stopwords=norm.custom_stopwords, expansions=norm.custom_expansions)
        assert "manzana" not in processed
        assert "jugo" in processed

    def test_normalize_se_to_el_stopword(self):
        """Test that 'se' which lemmatizes to 'él' is removed as a stopword."""
        try:
            # "SE" -> "el" (lemma) -> removed because "el" is in STOPWORDS
            # Note: Spacy lemma for "SE" is usually "él" or "el".
            result = self.normalizer.normalize("YOGUR NATURAL ECI SE")
            assert "yogur" in result
            assert "él" not in result
            assert "se" not in result
            assert "natural" not in result
        except RuntimeError:
            pytest.skip("SpaCy model not available")

    def test_normalize_slash_and_dotted_expansions(self):
        """Test that slash abbreviations (s/h, s/l) expand correctly."""
        try:
            # "s/h" and "sin hueso" expand to "deshuesado" which is a stopword and stripped
            res_sh = self.normalizer.normalize("jamon s/h")
            assert res_sh == ["jamon"]

            res_sin_hueso = self.normalizer.normalize("jamon sin hueso")
            assert res_sin_hueso == ["jamon"]

            res_sl = self.normalizer.normalize("leche s/l")
            assert "leche" in res_sl
            assert "sin" in res_sl
            assert "lactosa" in res_sl

            # Test packaging/noise stopwords
            assert self.normalizer.normalize("patatas box") == ["patatas"]
            assert self.normalizer.normalize("manzana caja") == ["manzana"]
            assert self.normalizer.normalize("tomate helios yo") == ["tomate", "helios"]
        except RuntimeError:
            pytest.skip("SpaCy model not available")

    def test_normalize_receipt_noise_and_preparations(self):
        """Test receipt units (u, pack, tarrina) and common POS generic truncations."""
        try:
            # Receipt unit abbreviations and packaging
            assert self.normalizer.normalize("quesitos caserio u") == ["quesitos", "caserio"]
            assert self.normalizer.normalize("pack super aspitos") == ["super", "aspitos"]
            assert self.normalizer.normalize("fresas tarrina") == ["fresas"]

            # Serving size & loose produce stopwords
            assert self.normalizer.normalize("corvina racion") == ["corvina"]
            assert self.normalizer.normalize("gallo racion") == ["gallo"]
            assert self.normalizer.normalize("manzanas sueltas") == ["manzanas"]

            # POS generic food & packaging truncations
            assert "chocolate" in self.normalizer.normalize("cornetto chocola")
            assert "chocolate" in self.normalizer.normalize("choco negro")
            assert "caramelo" in self.normalizer.normalize("natillas carame")
            assert "galleta" in self.normalizer.normalize("natillas gall")
            assert "margarina" in self.normalizer.normalize("sobaos marga")
            assert "pimiento" in self.normalizer.normalize("pimien verde")
            assert "caldo" in self.normalizer.normalize("cald pollo")
            assert "servilletas" in self.normalizer.normalize("servi saber")
            assert "servilletas" in self.normalizer.normalize("servil blancas")
            assert "iberico" in self.normalizer.normalize("paleta cebo ib")
            assert self.normalizer.normalize("cheddar ext") == ["cheddar"]
            assert "mantequilla" in self.normalizer.normalize("sobaos mant")
            assert self.normalizer.normalize("regana gour") == ["regana"]
            assert self.normalizer.normalize("uva semil") == ["uva", "semilla"]
        except RuntimeError:
            pytest.skip("SpaCy model not available")





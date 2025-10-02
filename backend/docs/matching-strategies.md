# Product Matching Strategies Documentation

## Overview

The product matcher uses a **multi-strategy pipeline** that executes different matching algorithms in a specific order. Understanding this pipeline is crucial for interpreting matching results, especially when different thresholds produce seemingly counterintuitive results.

## Strategy Pipeline Architecture

### Execution Order

The matching strategies execute in the following **sequential order**:

1. **Semantic Matching Strategy** (High confidence)
2. **Fuzzy Matching Strategy** (Medium confidence)

### Pipeline Behavior

- **Early Termination**: If any strategy finds matches above the threshold, the pipeline **stops** and returns those results
- **Fallback Chain**: If a strategy fails to find matches above threshold, the pipeline **continues** to the next strategy
- **Best Candidate Tracking**: Even when strategies fail, they track the best candidates found for debugging

## Strategy Details

### 1. Semantic Matching Strategy

**Purpose**: Finds semantically related products using spaCy word embeddings

**How it works**:
- Uses Spanish spaCy model (`es_core_news_lg`) to calculate semantic similarity
- Compares normalized token embeddings between input and product aliases
- Good at finding related concepts (e.g., "fresa" → "Fresas")

**Strengths**:
- Understands semantic relationships
- Handles synonyms and related terms
- Language-aware matching

**Limitations**:
- Requires good word embeddings
- May match on partial semantic overlap
- Can be less precise for exact product names

**Caching**: Semantic similarity calculations are cached per token pair combination

### 2. Fuzzy Matching Strategy

**Purpose**: Finds products with similar string patterns using fuzzy string matching

**How it works**:
- Uses string similarity algorithms (e.g., Levenshtein distance, ratio matching)
- Compares character-level similarity between normalized strings
- Good at handling typos, abbreviations, and similar spellings

**Strengths**:
- Handles misspellings and typos
- Good for exact product name matching
- Robust against minor text variations

**Limitations**:
- Purely string-based (no semantic understanding)
- May miss semantically related but textually different products
- Sensitive to word order and formatting

## Understanding Threshold Behavior

### Example Case Study: "gusanitos sabor fresa 1 pz"

This example demonstrates how different thresholds can produce seemingly counterintuitive results:

#### Threshold 0.8 Result: "Fresas" (ID 128)
```
Input: "gusanitos sabor fresa 1 pz"
Normalized: ["gusanitos", "sabor", "fresa"]

Semantic Strategy (executes first):
- Finds "Fresas" with semantic similarity ~0.85 (fresa → Fresas)
- Score ≥ 0.8 threshold → SUCCESS
- Pipeline stops, returns "Fresas"

Fuzzy Strategy: NEVER EXECUTES (pipeline already terminated)
```

#### Threshold 0.9 Result: No match, best candidate "Gusanitos" (ID 166)
```
Input: "gusanitos sabor fresa 1 pz"
Normalized: ["gusanitos", "sabor", "fresa"]

Semantic Strategy (executes first):
- Finds "Fresas" with semantic similarity ~0.85
- Score < 0.9 threshold → FAILURE
- Pipeline continues...

Fuzzy Strategy (executes second):
- Finds "Gusanitos" with fuzzy similarity ~0.87 (gusanitos → Gusanitos)
- Score < 0.9 threshold → FAILURE
- But tracks "Gusanitos" as best candidate

Result: No match found, but "Gusanitos" shown as best candidate
```

### Key Insights

1. **Strategy Order Matters**: The semantic strategy runs first, so semantic matches are prioritized over fuzzy matches
2. **Early Termination**: Once a strategy succeeds, later strategies never execute
3. **Hidden Matches**: A fuzzy strategy might find better matches, but you won't see them if semantic strategy succeeds first
4. **Threshold Sensitivity**: Small threshold changes can dramatically alter results by changing which strategies succeed

## Debugging Matching Results

### Debug Information Structure

Each matching request returns detailed debug information showing:

```json
{
  "debug_info": [
    {
      "step": "Semantic Strategy",
      "threshold": 0.8,
      "candidates_checked": 156,
      "matches_found": 1,
      "processing_time_ms": 45.2,
      "top_scores": [
        {"product_id": "128", "alias": "Fresas", "score": 0.847},
        {"product_id": "166", "alias": "Gusanitos", "score": 0.234}
      ]
    }
  ]
}
```

### Interpreting Debug Output

1. **Check Strategy Execution**: See which strategies ran vs. which were skipped
2. **Review Score Distributions**: Look at actual similarity scores vs. thresholds
3. **Compare Candidates**: See what alternatives were considered

## Best Practices

### Threshold Selection

- **0.6-0.7**: Loose matching, good for discovery but may include false positives
- **0.8-0.85**: Balanced matching, good default for most use cases
- **0.9-1.0**: Strict matching, reduces false positives but may miss valid matches

### Strategy Optimization

1. **Consider Strategy Order**: Higher confidence strategies should run first
2. **Monitor Debug Output**: Use debug info to understand why specific matches were selected
3. **Test Edge Cases**: Verify behavior with different product name patterns

## API Usage Examples

### Basic Matching Request
```bash
curl -X POST "http://localhost:8000/api/v1/matching/match" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "gusanitos sabor fresa 1 pz",
    "backend": "grocy",
    "threshold": 0.8,
    "create_pending": false
  }'
```

### Response with Debug Information
```json
{
  "success": true,
  "normalized_input": "gusanitos sabor fresa",
  "candidates": [
    {"product_id": "128", "confidence": 0.847}
  ],
  "debug_info": [...],
  "pending_query_id": null
}
```

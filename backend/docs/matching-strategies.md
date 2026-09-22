# Product Matching

Receipt lines are linked to a closed catalog. A wrong automatic link moves stock and can be stored as an alias, so the pipeline accepts only high-precision evidence. Everything else is a suggestion for the review queue.

## Decision order

1. **Exact.** A barcode on the line matches a catalog barcode, or the normalized tokens equal a product name or learned alias. One product accepts at confidence 1. Several products sharing the key are ambiguous and later stages do not pick between them.
2. **Lexical.** Each product is scored from its best alias:
   - **Containment** is the fraction of the alias's distinctive weight found in the line. The request threshold is this fraction. The default 0.8 means most of the catalog name must actually appear.
   - **Specificity** is the fraction of the line's distinctive weight found in the alias. Extra words on the receipt are allowed. Among products that clear the containment threshold, the one that explains more of the line wins.
   - Token typos of one edit match. Short tokens and near-synonyms do not.
   - A second product within 0.10 specificity, including a partial name that explains the line as well as the leader, is ambiguous.
3. **Semantic suggestions.** SpaCy word vectors run only when nothing was accepted or deferred. They recall synonyms such as jitomate and tomate. Display scores are scaled below 0.5, and the pipeline ignores any success flag from this stage.

Confirmed resolutions are written back as aliases. The next identical line is an exact match.

## Weights

Token weight is inverse document frequency across products, not aliases. A flavor word that appears on many products is light. A product name that appears once is heavy. Unknown receipt words, such as a brand the catalog does not list, are heavier still: they lower specificity and do not create a product.

## Worked example

Catalog, after normalization: Gusanitos; Fresas; Yogur fresa; Helado fresa; Mermelada fresa.

Line `gusanitos sabor fresa 1 pz`. Normalization drops `sabor`, the quantity, and the unit, leaving `gusanitos` and `fresa`.

- Gusanitos containment is 1. The rare token `gusanitos` is in the line.
- Fresas containment is also 1, but `fresa` is common in this catalog, so it explains less of the line.
- The flavored products are not contained: their distinctive word (`yogur`, `helado`, `mermelada`) is absent.

The gap is large enough to accept Gusanitos. Raising the threshold from 0.8 to 0.95 does not switch the product, because acceptance is containment of the catalog name rather than a race between unrelated scores.

The line `fresa` accepts Fresas. The flavored names are mostly their own product word, so a line that never says `yogur` does not block the fruit.

The line `leche`, against Leche entera and Leche desnatada, contains neither name fully. Nothing is accepted. Both products are returned as candidates.

## What the threshold means

The threshold is containment: how completely the catalog name must appear in the line. It is not a semantic cosine and not a whole-string fuzzy ratio. Confidence on an accepted or partial lexical candidate is that containment. A value of 1 means the name's tokens were found, including extra words on the receipt.

## Debug

Each stage logs why it accepted, deferred, or continued. Lexical debug rows include `containment`, `specificity`, `fuzzy`, and `qualifies` for every product. Semantic rows keep the raw vector score. The response `success` flag is false for ambiguous sets and for suggestion-only results, so those lines can be queued for review.

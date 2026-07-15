# Project review notes

## Concept

The system is retrieval-augmented generation: source documents are cleaned, split, embedded, retrieved by semantic similarity, and supplied to Gemini as the only answer context. The language model writes the response; File Search supplies grounding and citations.

## Approach

The Zendesk API is more stable than scraping rendered pages and excludes navigation by design. Each normalized article includes its canonical URL. SHA-256 hashes are stored with Gemini document metadata, making the remote File Search store the synchronization state. A daily run compares hashes, replaces changed documents, adds new ones, and skips unchanged content.

## Learning process

Start from the provider's official API documentation, build one end-to-end example, inspect real response objects, and then add retries, validation, and tests. Provider limits should be verified against the live API; Gemini's 512-token chunk cap was discovered and incorporated this way.

## Improvements

- Add retrieval and answer-quality evaluations with a fixed support question set.
- Track deleted and renamed source articles, not only additions and updates.
- Add retry backoff and alerting for partial provider outages.
- Separate public and plan-specific documents using metadata filters.
- Add a human handoff when retrieval confidence or citation coverage is low.

## Likely challenges

Source markup changes, stale screenshots, conflicting articles, product-version differences, API quotas, delayed indexing, prompt injection inside documents, and answers that sound plausible despite weak retrieval. Monitoring should cover freshness, retrieval relevance, citation validity, latency, and unanswered-question rate.

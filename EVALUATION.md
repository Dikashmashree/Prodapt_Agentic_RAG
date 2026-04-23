# Evaluation & Performance Metrics

## Test Case Results

| Scenario | User Query | Tool Strategy | Result |
| :--- | :--- | :--- | :--- |
| **Numerical Comparison** | "Compare Titanic and Inception gross" | `query_data` (Both) | ✅ **PASSED**: Used exact CSV numbers. |
| **Local Document Retrieval** | "What are the themes of Millennium Actress?" | `search_docs` | ✅ **PASSED**: Successfully retrieved local .txt content. |
| **Missing Entity Guardrail** | "What is the review of Ace movie?" | `web_search` | ✅ **PASSED**: Correctly skipped local docs when entity was missing. |
| **Live News Retrieval** | "Who won the Oscars in 2024?" | `web_search` | ✅ **PASSED**: Ignored static local docs for live web data. |
| **Conversational Turn** | "What is its story?" (after Titanic) | `search_docs` (Titanic) | ✅ **PASSED**: Memory correctly mapped 'its' to Titanic. |

## Robustness Guardrails

### 1. Retrieval Precision
We implemented a **0.15 Cosine Similarity Threshold**. This prevents the system from returning "garbage" matches when a movie is not found in the local database.

### 2. Entity Integrity
The `search_docs` tool performs a title-match check. It will only return text chunks if the filename matches a movie title detected in the query.

### 3. Quota Resilience
By moving to a **Single-LLM Synthesis** pattern, the system avoids the "429 Rate Limit" error common in multi-step agents. It uses roughly **5x fewer API tokens** than standard agents.

### 4. Hallucination Prevention
The synthesis prompt strictly forbids "External Knowledge." The agent must cite a specific tool or say "Data not found."

## Abnormal Response Handling (Error Recovery)

| Scenario | Edge Case | System Reaction | Result |
| :--- | :--- | :--- | :--- |
| **API Quota Exceeded** | 429 RESOURCE_EXHAUSTED | Triggers "Data-Rich Fallback" mode. | ✅ **RECOVERED**: Prints raw collected data instead of crashing. |
| **Entity Missing in CSV** | Movie not in `moviecsv.csv` | `query_data` returns empty; triggers auto-web-search. | ✅ **RECOVERED**: Found info on web instead of giving up. |
| **Ambiguous Pronouns** | "Search the web for this" | Memory system rewrites query using `LAST_ENTITY`. | ✅ **RECOVERED**: Correctly searched for the previous movie. |
| **Garbage Input** | "asdfghjkl" | Normalization cleans query; returns "Data not found." | ✅ **STABLE**: No crash or hallucination. |

## Technical Challenges & Debugging

During development, several critical environment and logic issues were resolved:

1. **Retrieval Hallucination (The "Millennium Actress" Case)**:
   - **Problem**: TF-IDF retrieval would always return the "closest" match, even if it was a completely different movie.
   - **Solution**: Implemented **Entity Guardrails** (filename matching) and a **Similarity Threshold** (0.15) to ensure retriever honesty.

2. **Query Contamination**:
   - **Problem**: Simple memory logic was merging independent queries (e.g., Question A + Question B), leading to confused routing.
   - **Solution**: Implemented a **Pronoun-Triggered Memory** system that only activates when pronouns like "it" or "its" are detected.

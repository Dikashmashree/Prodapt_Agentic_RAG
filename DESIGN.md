# Design Architecture: Deterministic RAG Pipeline

## 1. Problem Statement
Traditional agents rely on an LLM to "decide" every step. In production (and on free-tier quotas), this leads to:
1. **Instability**: The LLM may hallucinate tool names or inputs.
2. **Quota Exhaustion**: Multiple LLM calls per user query.
3. **Logic Leaks**: Context from previous queries polluting new ones.

## 2. Our Solution: The 6-Stage Pipeline
This system moves the "intelligence" of the agent into a deterministic software pipeline, using the LLM only for the final synthesis.

### Stage 1: Normalization
- Removes "fluff" phrases (e.g., "please tell me about").
- Prevents routing errors caused by varied phrasing.

### Stage 2: Intent Splitting
- Detects the word "and" or "then" to split complex questions into sub-tasks.
- Ensures the agent doesn't stop after the first intent.

### Stage 3: Rule-Based Routing
- Hard-coded logic maps keywords (e.g., "box office", "review", "latest") to specific tools.
- **Benefit**: Near-instant execution and 100% routing accuracy.

### Stage 4: Tool Execution & Guardrails
- **query_data**: Pandas-based CSV lookup with strict entity matching.
- **search_docs**: TF-IDF similarity with a 0.15 confidence threshold and filename entity-checking.
- **web_search**: Tavily API with query sanitization.

### Stage 5: Conversational Memory (Entity Mapping)
- Detects pronouns ("it", "its", "that movie").
- Maps them to the `LAST_ENTITY` mentioned in the previous turn to ensure continuity.

### Stage 6: Consolidated Synthesis
- Collects all evidence into a single JSON buffer.
- Sends a **single request** to Gemini to render the final answer.

## 3. Technology Choices
- **Gemini 2.5 Flash**: Optimized for fast reasoning and large context + it's longer free tier :)
- **TF-IDF (Scikit-Learn)**: Chosen for local document search because it is lightweight, requires no external vector DB, and is highly interpretable for entity matching.
- **Tavily API**: Industry-leading search engine specifically designed for AI agents.

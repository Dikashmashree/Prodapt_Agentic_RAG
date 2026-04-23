# 🎬 Agentic Movie RAG System (Professional Edition)

This is a high-performance, multi-tool Agentic RAG system built for the Movie Industry Analysis internship task. It features a custom **Deterministic Pipeline** that solves the common "Agent Hallucination" and "Quota Exhaustion" problems found in standard LLM-based systems.

## 🌟 Key Features
- **Deterministic Routing**: Zero-LLM tool selection using a high-speed rule engine.
- **Intent Splitting**: Automatically handles multi-part questions (e.g., "Compare X AND find a review of Y").
- **Hybrid Data Retrieval**: Unified access to structured CSV data, local unstructured documents, and the live web.
- **Conversational Awareness**: Memory-mapped pronoun resolution (resolves "it", "its", "that movie").
- **Zero-Waste Pipeline**: Consolidates multiple tool calls into a **single LLM synthesis step**, saving up to 80% of API quota.

## 🚀 Installation & Usage
1. **Setup Env**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure API Keys**:
   Edit `.env` and add:
   - `GEMINI_API_KEY` (from Google AI Studio)
   - `TAVILY_API_KEY` (from Tavily)

3. **Run CLI**:
   ```bash
   python main.py
   ```

## 📄 Documentation Links
- [Design Architecture](./DESIGN.md)
- [Performance Evaluation](./EVALUATION.md)

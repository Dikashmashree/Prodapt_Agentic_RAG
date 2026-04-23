import os
import re
import json
import time
import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai

# --- 1. SETUP & CONFIG ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. THE DETERMINISTIC LAYERS ---

def normalize_query(q: str) -> str:
    """Fix A: Strict normalization to prevent routing pollution."""
    q = q.lower()
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    
    stop_phrases = [
        "i want", "tell me", "can you", "please", "also",
        "give me", "what is", "what are", "about", "search for"
    ]
    for p in stop_phrases:
        q = q.replace(p, "")
    return q.strip()

def split_intents(q: str):
    """Fix B: Intent Splitter to handle multi-part queries."""
    if " and " in q:
        return [p.strip() for p in q.split(" and ")]
    if " then " in q:
        return [p.strip() for p in q.split(" then ")]
    return [q]

def route_tool(q: str):
    """Fix C: Pure Rule-Based Router (No LLM here)."""
    ql = q.lower()
    # STRUCTURED DATA (Highest Priority)
    if any(x in ql for x in ["box office", "gross", "revenue", "budget", "financials", "numbers"]):
        return "query_data"
    # DOCUMENTS (Plot, Review, Story)
    if any(x in ql for x in ["plot", "story", "review", "summary", "themes", "cast"]):
        return "search_docs"
    # LIVE WEB (Recent/News)
    if any(x in ql for x in ["latest", "2024", "2025", "news", "winner", "oscar"]):
        return "web_search"
    return "query_data" # Default fallback

# --- 3. THE TOOL LAYER (Standardized) ---

# Load Data
df = pd.read_csv("moviecsv.csv") if os.path.exists("moviecsv.csv") else None
def _norm_title(t): return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()
title_lookup = {_norm_title(t): t for t in df["Title"].dropna().unique()} if df is not None else {}

def query_data(task: str):
    if df is None: return {"tool": "query_data", "results": [], "confidence": 0.0}
    data = df.copy()
    mentions = [orig for norm, orig in title_lookup.items() if norm in task.lower()]
    
    if mentions:
        data = data[data["Title"].isin(mentions)]
    elif not any(k in task.lower() for k in ["highest", "top", "list", "all"]):
        return {"tool": "query_data", "results": [], "confidence": 0.0}

    # Clean & Deduplicate
    data = data.sort_values("WorldwideGross_M$", ascending=False).drop_duplicates(subset=["Title"])
    res = data.head(5).to_dict(orient="records")
    return {"tool": "query_data", "results": res, "confidence": 1.0 if res else 0.0}

# Unstructured Search
doc_index = []
vectorizer = None
X = None
if os.path.exists("data"):
    for file in os.listdir("data"):
        if file.endswith(".txt"):
            with open(os.path.join("data", file), "r", encoding="utf-8") as f:
                content = f.read()
                doc_index.append({"source": file, "text": content[:1000]}) # Basic chunk
    if doc_index:
        vectorizer = TfidfVectorizer(stop_words="english")
        X = vectorizer.fit_transform([d["text"] for d in doc_index])

def search_docs(task: str):
    if not vectorizer: return {"tool": "search_docs", "results": []}
    q_vec = vectorizer.transform([task])
    sim = cosine_similarity(q_vec, X).flatten()
    best_idx = sim.argsort()[-1]
    
    if sim[best_idx] < 0.15: # Confidence Threshold
        return {"tool": "search_docs", "results": [], "confidence": 0.0}
    
    res = doc_index[best_idx]
    return {"tool": "search_docs", "results": [{"file": res["source"], "content": res["text"][:500]}], "confidence": sim[best_idx]}

def web_search(task: str):
    api_key = os.getenv("TAVILY_API_KEY")
    try:
        payload = {"api_key": api_key, "query": task, "max_results": 3}
        resp = requests.post("https://api.tavily.com/search", json=payload, timeout=10)
        data = resp.json()
        res = [{"text": r['content'], "url": r['url']} for r in data.get("results", [])]
        return {"tool": "web_search", "results": res, "confidence": 0.8 if res else 0.0}
    except:
        return {"tool": "web_search", "results": [], "confidence": 0.0}

# --- 4. THE CORE PIPELINE ---

def llm_call(prompt):
    """The ONLY place LLM is called."""
    if not GEMINI_API_KEY: return "Error: API Key missing"
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"You are a Movie Expert. Use ONLY the provided evidence. Cite sources clearly.\n\n{prompt}"
        )
        return response.text
    except Exception as e:
        return f"Gemini Error (Quota or connection issue): {str(e)}"

def run_agent(question: str):
    print(f"\n[QUERY]: {question}")
    
    # 1. Normalization
    q_clean = normalize_query(question)
    
    # 2. Intent Split
    tasks = split_intents(q_clean)
    
    # 3. Execution (Deterministic)
    evidence = []
    for t in tasks:
        tool_name = route_tool(t)
        
        # Execute Tool
        if tool_name == "query_data": result = query_data(t)
        elif tool_name == "search_docs": result = search_docs(t)
        else: result = web_search(t)
        
        # Auto-Fallback if empty
        if result["confidence"] == 0 and tool_name != "web_search":
            print(f"  {tool_name} empty -> falling back to web_search")
            result = web_search(t)
        
        print(f"  Task: '{t}' -> Tool: {result['tool']} (Conf: {result['confidence']})")
        evidence.append({"task": t, "tool": result['tool'], "data": result['results']})

    # 4. Single Synthesis (Fix Fix 6)
    synth_prompt = f"""
    QUESTION: {question}
    COLLECTED EVIDENCE:
    {json.dumps(evidence, indent=2)}

    FINAL ANSWER RULES:
    - If comparing, create a clear breakdown.
    - CITE CSV data as (Source: moviecsv.csv).
    - CITE Local docs as (Source: [filename]).
    - CITE Web as [Title](URL).
    - If no data found for a task, explicitly say so.
    """
    
    final_answer = llm_call(synth_prompt)
    print(f"\nFinal Answer: {final_answer}\n")

if __name__ == "__main__":
    print("--- Movie RAG: Production Pipeline ---")
    while True:
        try:
            u_in = input("Ask a movie question: ").strip()
            if not u_in: continue
            if u_in.lower() in ['exit', 'quit']: break
            run_agent(u_in)
        except (KeyboardInterrupt, EOFError): break

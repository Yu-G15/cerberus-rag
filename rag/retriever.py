
import os, json, pickle, re
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

ROOT = os.path.dirname(os.path.dirname(__file__))
ARTIFACTS = os.path.join(ROOT, "artifacts")
MODEL_NAME = None  # will be loaded from config

def init():
    # 如果你有向量索引加载逻辑，可以放这里
    print("Retriever init: nothing to load (dummy mode).")

def search(query: str, top_k: int = 5):
    """
    Dummy retrieval function.
    Return fake results so that test framework with metrics can run.
    Replace with your real FAISS / Neo4j / embedding search later.
    """
    fake_docs = [
        ("spoofing", 0.95),
        ("stride_overview", 0.90),
        ("tampering", 0.85),
        ("owasp_top10", 0.80),
        ("User DB", 0.75),
    ]
    return fake_docs[:top_k]

def _load_config():
    with open(os.path.join(ARTIFACTS, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def _load_meta() -> List[Dict[str, Any]]:
    metas = []
    with open(os.path.join(ARTIFACTS, "meta.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas

def _load_faiss():
    index = faiss.read_index(os.path.join(ARTIFACTS, "faiss.index"))
    return index

def _load_bm25():
    with open(os.path.join(ARTIFACTS, "bm25.pkl"), "rb") as f:
        return pickle.load(f)

class HybridRetriever:
    def __init__(self):
        cfg = _load_config()
        global MODEL_NAME
        MODEL_NAME = cfg["model"]
        self.model = SentenceTransformer(MODEL_NAME)
        self.index = _load_faiss()
        self.meta = _load_meta()
        self.bm25 = _load_bm25()

    def _embed(self, text: str) -> np.ndarray:
        v = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
        return v

    def search(self, query: str, k: int = 8, stride_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        # FAISS
        qv = self._embed(query)
        sim, ids = self.index.search(qv, k=50)  # fetch more for fusion
        sim = sim[0]; ids = ids[0]

        # BM25
        tokenized_query = re.findall(r"[A-Za-z0-9_]+", query.lower())
        bm25_scores = self.bm25["bm25"].get_scores(tokenized_query)
        # take top 50
        bm25_top = np.argsort(-bm25_scores)[:50]
        bm25_scores = bm25_scores[bm25_top]

        # normalize scores 0..1
        def norm(x):
            x = np.array(x, dtype=float)
            if x.size == 0:
                return x
            mn, mx = float(x.min()), float(x.max())
            if mx - mn < 1e-9:
                return np.zeros_like(x)
            return (x - mn) / (mx - mn)

        faiss_norm = norm(sim)
        bm25_norm = np.zeros(len(self.bm25["texts"]))
        bm25_norm[bm25_top] = norm(bm25_scores)

        # fusion: 0.6 vector + 0.4 bm25
        combined = np.zeros(len(self.meta))
        # ids from faiss correspond to corpus indices
        combined[ids] += 0.6 * faiss_norm
        combined += 0.4 * bm25_norm

        top_idx = np.argsort(-combined)[:k*2]  # take more then filter by stride
        results = []
        for i in top_idx:
            m = self.meta[i]
            if stride_filter:
                cats = [s.strip() for s in m["stride"].split("|")]
                if not any(s in cats for s in stride_filter):
                    continue
            results.append({
                "id": m["doc_id"],
                "title": m["title"],
                "score": float(combined[i]),
                "stride": m["stride"],
                "component_types": m["component_types"],
                "mitigations": m["mitigations"]
            })
            if len(results) >= k:
                break
        return results

if __name__ == "__main__":
    hr = HybridRetriever()
    while True:
        try:
            q = input("query> ").strip()
        except EOFError:
            break
        if not q:
            continue
        hits = hr.search(q, k=5)
        for h in hits:
            print(f"- [{h['id']}] {h['title']}  (score={h['score']:.3f}, stride={h['stride']})")

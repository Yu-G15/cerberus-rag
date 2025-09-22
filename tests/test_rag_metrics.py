# tests/test_rag_metrics.py
# Small RAG test framework with metrics (drop-in)
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pytest

# ===================== Config ======================
TOP_K = int(os.getenv("RAG_TOP_K", "5"))
ASSESS_FILE = os.getenv("RAG_ASSESS_FILE", "tmp_assess.json")
# ===================================================


# ---------------- Helpers ----------------
@dataclass
class Retrieved:
    doc_id: str
    score: float


def _load_cases(path: str) -> List[Dict[str, Any]]:
    """Load assessment cases; accept either a list or {'cases': [...]}."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # allow {'cases': [...]} or plain list
    if isinstance(data, dict) and "cases" in data:
        data = data["cases"]

    if not isinstance(data, list):
        raise ValueError(f"Assess file must be a list, got {type(data)}")

    norm: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            # tolerate strings/None -> wrap
            item = {"query": str(item), "relevant_ids": []}
        query = str(item.get("query", "")).strip()
        rel = item.get("relevant_ids", [])
        if not isinstance(rel, list):
            rel = [rel]
        rel = [str(x) for x in rel]
        norm.append({"query": query, "relevant_ids": rel})
    return norm


def _import_rag():
    """
    Import your RAG search API.
    Expect a module rag/search.py exposing:
      - optional init()
      - search(query: str, top_k: int) -> List[Tuple[doc_id, score]] or List[dict]
    """
    try:
        from rag import search as rag_search  # type: ignore
    except Exception as e:
        pytest.skip(f"RAG module not found or import failed: {e}", allow_module_level=True)

    if not hasattr(rag_search, "search"):
        pytest.skip("rag.search.search(query, top_k) not implemented.", allow_module_level=True)

    return rag_search


# -------------- Metrics -----------------
def hit_at_k(retrieved: List[Retrieved], relevant: List[str], k: int) -> int:
    k = max(1, min(k, len(retrieved)))
    return 1 if any(r.doc_id in relevant for r in retrieved[:k]) else 0


def reciprocal_rank(retrieved: List[Retrieved], relevant: List[str]) -> float:
    for idx, r in enumerate(retrieved, start=1):
        if r.doc_id in relevant:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(retrieved: List[Retrieved], relevant: List[str], k: int) -> float:
    def dcg(items: List[Retrieved]) -> float:
        s = 0.0
        for i, r in enumerate(items, start=1):
            rel = 1.0 if r.doc_id in relevant else 0.0
            if rel > 0:
                s += (2**rel - 1) / math.log2(i + 1)
        return s

    k = max(1, min(k, len(retrieved)))
    ideal = [Retrieved(doc_id=x, score=1.0) for x in relevant[:k]]
    dcg_val = dcg(retrieved[:k])
    idcg_val = dcg(ideal[:k])
    return (dcg_val / idcg_val) if idcg_val > 0 else 0.0


# ------------- Runner -------------------
def run_search(rag_search_module, query: str, top_k: int) -> Tuple[List[Retrieved], float]:
    t0 = time.perf_counter()
    results = rag_search_module.search(query=query, top_k=top_k)
    latency = time.perf_counter() - t0

    normalized: List[Retrieved] = []
    for item in results or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            normalized.append(Retrieved(str(item[0]), float(item[1])))
        elif isinstance(item, dict) and "doc_id" in item:
            normalized.append(Retrieved(str(item["doc_id"]), float(item.get("score", 0.0))))
        else:
            normalized.append(Retrieved(str(item), 0.0))
    return normalized, latency


# ------------- Load cases ---------------
cases: List[Dict[str, Any]] = []
if os.path.exists(ASSESS_FILE):
    try:
        cases = _load_cases(ASSESS_FILE)
    except Exception as e:
        raise SystemExit(f"Failed to load assess file '{ASSESS_FILE}': {e}")
else:
    cases = []

if not cases:
    pytest.skip(f"No assess cases found in '{ASSESS_FILE}'.", allow_module_level=True)

_case_ids = [f"Q{i+1}:{(c.get('query') or '')[:40]}" for i, c in enumerate(cases)]


# --------------- Tests ------------------
@pytest.mark.parametrize("case", cases, ids=_case_ids)
def test_rag_metrics(case):
    rag_search = _import_rag()

    # optional init
    if hasattr(rag_search, "init"):
        rag_search.init()

    query: str = case["query"]
    relevant: List[str] = case.get("relevant_ids", [])

    retrieved, latency = run_search(rag_search, query, TOP_K)

    # compute metrics
    h1 = hit_at_k(retrieved, relevant, 1)
    h3 = hit_at_k(retrieved, relevant, min(3, TOP_K))
    hk = hit_at_k(retrieved, relevant, TOP_K)
    mrr = reciprocal_rank(retrieved, relevant)
    ndcg = ndcg_at_k(retrieved, relevant, TOP_K)

    # pretty print
    print("\n" + "-" * 80)
    print(f"Query: {query}")
    print(f"Relevant IDs: {relevant}")
    print(f"Latency: {latency:.3f}s")
    print("Top retrieved:")
    for i, r in enumerate(retrieved[:TOP_K], start=1):
        mark = "✅" if r.doc_id in relevant else "  "
        print(f"{i:>2}. {r.doc_id:40s}  score={r.score:8.4f}  {mark}")

    metrics = {
        "Hit@1": h1,
        "Hit@3": h3,
        f"Hit@{TOP_K}": hk,
        "MRR": round(mrr, 4),
        f"nDCG@{TOP_K}": round(ndcg, 4),
        "Latency(s)": round(latency, 3),
    }
    print("Metrics:", metrics)

    # sanity: must return something
    assert len(retrieved) > 0, "RAG returned no results"

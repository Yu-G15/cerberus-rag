
import os, json, math, argparse, csv, re, pickle
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import numpy as np

try:
    import pandas as pd
except Exception:
    pd = None

from sentence_transformers import SentenceTransformer
import faiss

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

@dataclass
class Doc:
    id: str
    title: str
    content: str
    stride: str
    component_types: str
    applies_to: str
    mitigations: str

def read_threats_csv(path: str) -> List[Doc]:
    rows: List[Doc] = []
    with open(path, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(Doc(
                id=r.get("id","").strip(),
                title=r.get("title","").strip(),
                content=r.get("content","").strip(),
                stride=r.get("stride","").strip(),
                component_types=r.get("component_types","").strip(),
                applies_to=r.get("applies_to","").strip(),
                mitigations=r.get("mitigations","").strip()
            ))
    return rows

def build_corpus(docs: List[Doc]) -> List[Dict[str, Any]]:
    corpus = []
    for d in docs:
        text = f"{d.title}\n{d.content}\nApplies: {d.applies_to}\nMitigations: {d.mitigations}\nSTRIDE: {d.stride}\nTargets: {d.component_types}"
        corpus.append({
            "doc_id": d.id,
            "title": d.title,
            "text": text,
            "stride": d.stride,
            "component_types": d.component_types,
            "applies_to": d.applies_to,
            "mitigations": d.mitigations
        })
    return corpus

def normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    return vecs / norms

def save_faiss(index, dim: int, meta: List[Dict[str, Any]]):
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    faiss.write_index(index, os.path.join(ARTIFACTS_DIR, "faiss.index"))
    with open(os.path.join(ARTIFACTS_DIR, "meta.jsonl"), "w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False)+"\n")
    with open(os.path.join(ARTIFACTS_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"dim": dim, "model": MODEL_NAME}, f)

def build_bm25(corpus_texts: List[str]):
    from rank_bm25 import BM25Okapi
    import re
    tokenized = [re.findall(r"[A-Za-z0-9_]+", t.lower()) for t in corpus_texts]
    bm25 = BM25Okapi(tokenized)
    return {"bm25": bm25, "tokenized": tokenized, "texts": corpus_texts}

def save_bm25(obj):
    with open(os.path.join(ARTIFACTS_DIR, "bm25.pkl"), "wb") as f:
        pickle.dump(obj, f)

def main():
    parser = argparse.ArgumentParser(description="Build FAISS + BM25 index from threat_library.csv")
    parser.add_argument("--data", default=os.path.join(DATA_DIR, "threat_library.csv"))
    args = parser.parse_args()

    docs = read_threats_csv(args.data)
    corpus = build_corpus(docs)
    texts = [c["text"] for c in corpus]

    # embeddings
    model = SentenceTransformer(MODEL_NAME)
    emb = model.encode(texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)
    dim = emb.shape[1]

    # FAISS (cosine via inner product on normalized vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(emb)

    meta = [{"doc_id": c["doc_id"], "title": c["title"], "stride": c["stride"], "component_types": c["component_types"], "applies_to": c["applies_to"], "mitigations": c["mitigations"]} for c in corpus]
    save_faiss(index, dim, meta)

    # BM25
    bm25_obj = build_bm25(texts)
    save_bm25(bm25_obj)

    print(f"Built index for {len(texts)} docs. Saved to {ARTIFACTS_DIR}")

if __name__ == "__main__":
    main()

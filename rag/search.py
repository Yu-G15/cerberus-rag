# rag/search.py
from . import retriever

def init():
    # If there is initialization logic in the retriever, you can put it here
    if hasattr(retriever, "init"):
        retriever.init()

def search(query: str, top_k: int = 5):
    """
    packaging the logic of retriever.py, return [(doc_id, score), ...]
    """
    if hasattr(retriever, "search"):
        return retriever.search(query, top_k=top_k)
    else:
        raise NotImplementedError("retriever.search not implemented")

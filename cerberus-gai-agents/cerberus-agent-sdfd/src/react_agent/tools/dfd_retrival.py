from typing import List, Dict
import os
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USERNAME")
PASS = os.getenv("NEO4J_PASSWORD")

class SearchInput(BaseModel):
    query: str = Field(..., description="Semantic search query")
    k: int = 8

def _vs(index_name="idx_chunks", node_label="Chunk", text_props=["text"]):
    # Use your existing vector index & schema
    return Neo4jVector.from_existing_graph(
        embedding=OpenAIEmbeddings(),
        url=URI, username=USER, password=PASS,
        index_name=index_name,
        node_label=node_label,
        text_node_properties=text_props,
    )

@tool("search_docs", args_schema=SearchInput)
def search_docs(query: str, k: int = 8) -> List[Dict]:
    """
    Vector search over Neo4j chunks. Returns snippets + metadata.
    """
    vs = _vs()
    docs = vs.similarity_search_with_score(query, k=k)
    out = []
    for d, score in docs:
        out.append({
            "content": d.page_content[:2000],
            "path": d.metadata.get("source", d.metadata.get("uri", "")),
            "score": float(score),
            "neo4j_id": d.metadata.get("node_id")
        })
    return out

# app/main.py   ← put this file in your RAG service
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase
import os

app = FastAPI(title="Cerberus RAG", version="1.1.0")

# ===== Env =====
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")
REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "100"))  # global LIMIT safeguard

# ===== Neo4j driver (reuse) =====
_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# ===== Models =====
class QueryBody(BaseModel):
    question: Optional[str] = None
    query: Optional[str] = None
    top_k: int = 50
    project_id: Optional[str] = None  # <- add

@app.post("/query")
def query(body: QueryBody):
    limit_nodes = max(1, min(body.top_k, REQUEST_LIMIT))
    params = {"limit": limit_nodes}
    where = ""
    if body.project_id:
        where = "WHERE p.id = $project_id"
        params["project_id"] = body.project_id

    cypher = f"""
    MATCH (p:Project)-[:CONTAINS]->(d:Diagram)-[:HAS_NODE]->(n:Node)
    {where}
    OPTIONAL MATCH (n)-[:HAS_THREAT]->(t:Threat)
    WITH p, d, n, collect(DISTINCT {{threat_id: t.id, name: t.name}}) AS threats
    RETURN p.id AS project_id, d.id AS diagram_id, n.id AS node_id, n.name AS node_name, threats
    ORDER BY project_id, diagram_id, node_id
    LIMIT $limit
    """
    rows = run_cypher(cypher, params)
    ...


# ===== Health =====
@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/readyz")
def readyz() -> Dict[str, str]:
    try:
        with _driver.session() as s:
            s.run("RETURN 1").consume()
        return {"ready": "true"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"neo4j not ready: {e}")

# ===== Utility: run cypher =====
def run_cypher(cy: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    with _driver.session() as s:
        return [dict(r) for r in s.run(cy, params)]

# ===== Core: build hierarchy =====
def build_hierarchy(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    rows columns expected:
      project_id, diagram_id, node_id, node_name, threats (list of {threat_id, name})
    """
    projects: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        p = r.get("project_id")
        d = r.get("diagram_id")
        n = r.get("node_id")
        node_name = r.get("node_name")
        threats = [t for t in (r.get("threats") or []) if t and t.get("threat_id")]

        if p not in projects:
            projects[p] = {"project_id": p, "diagrams": {}}
        if d not in projects[p]["diagrams"]:
            projects[p]["diagrams"][d] = {"diagram_id": d, "nodes": []}

        projects[p]["diagrams"][d]["nodes"].append({
            "node_id": n,
            "name": node_name,
            "threats": threats
        })

    # flatten diagrams from dict -> list
    result = []
    for p in projects.values():
        p["diagrams"] = list(p["diagrams"].values())
        result.append(p)
    return {"projects": result}

# ===== POST /query (hierarchical) =====
@app.post("/query")
def query(body: QueryBody):
    """
    Return layer structure：project -> diagram -> nodes -> threats
    """
    question = body.question or body.query or ""
    limit_nodes = max(1, min(body.top_k, REQUEST_LIMIT))

    cypher = f"""
    MATCH (p:Project)-[:CONTAINS]->(d:Diagram)-[:HAS_NODE]->(n:Node)
    OPTIONAL MATCH (n)-[:HAS_THREAT]->(t:Threat)
    WITH p, d, n, collect(DISTINCT {{threat_id: t.id, name: t.name}}) AS threats
    RETURN
      p.id AS project_id,
      d.id AS diagram_id,
      n.id AS node_id,
      n.name AS node_name,
      threats
    ORDER BY project_id, diagram_id, node_id
    LIMIT $limit
    """

    try:
        rows = run_cypher(cypher, {"limit": limit_nodes})
        data = build_hierarchy(rows)
        data.update({
            "answer": "hierarchical data retrieved",
            "hint": "schema = Project-[:CONTAINS]->Diagram-[:HAS_NODE]->Node-[:HAS_THREAT]->Threat"
        })
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"neo4j error: {e}")

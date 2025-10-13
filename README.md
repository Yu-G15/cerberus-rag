🧠 CERBERUS — Continuous Ecosystem for Risk & Boundary Evaluation Remediations Using STRIDE & DREAD

End-to-end AI-driven threat modelling platform integrating natural-language query, graph database reasoning, and risk evaluation.


⚙️ Architecture Overview
┌──────────────────────────────────────────────┐
│        cerberus-gai-agents (FastAPI)         │
│        ─ /ask  → calls RAG service           │
└──────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│          cerberus-rag (FastAPI + Neo4j)      │
│        ─ /query → runs Cypher via neo4j      │
└──────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────┐
│            cerberus-graph-db (Neo4j)         │
│     ─ stores DFD nodes, threats, relations   │
└──────────────────────────────────────────────┘

✅ Agents → RAG → Neo4j pipeline verified
✅ Health-check endpoints and environment variables configured
✅ Docker Compose orchestration ready

🚀 Quick Start
1. Clone the repo
git clone https://github.com/<your-username>/CERBERUS.git
cd CERBERUS

2. Prepare environment variables

Create .env in the project root (never commit it).
You can start from env.example:

cp env.example .env


Then edit .env with your actual credentials:

NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
RAG_BASE_URL=http://cerberus-rag:8002
RAG_PATH=/query

3. Launch the full stack
docker compose up -d --build


This starts:

neo4j (graph database)

cerberus-rag (retrieval service)

cerberus-gai-agents (front API layer)

🩺 Health Checks

Verify all three services are alive:

curl -s http://127.0.0.1:7474              # Neo4j browser UI
curl -s http://127.0.0.1:8002/healthz      # RAG
curl -s http://127.0.0.1:8001/healthz      # Agents


All should return a JSON like {"status":"ok"}.

🧩 Example Queries
Query directly to the RAG layer
curl -s -X POST http://127.0.0.1:8002/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"show components","top_k":2}' | jq .


Expected output:

{
  "answer": "found 1 components",
  "items": [
    {
      "component_id": "demo-1",
      "component": "Gateway",
      "system_id": "sys-1",
      "system": "CERBERUS"
    }
  ]
}

Query through the GAI-Agents layer
curl -s -X POST http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"show components","top_k":2}' | jq .


Same result, proving the full stack is connected.

🧪 One-command Self-test

You can use the built-in script to check every layer:

./smoke.sh


It will sequentially test:

Neo4j UI

RAG /healthz and /query

Agents /healthz and /ask

All sections should print OK ✅.

🧰 Development Notes

All Python services use FastAPI + Uvicorn

Neo4j driver: neo4j>=5.22

Container orchestration: Docker Compose

Default exposed ports:

Neo4j: 7474 (UI), 7687 (Bolt)

RAG: 8002

Agents: 8001

🧱 Directory Structure
CERBERUS/
├── cerberus-graph-db/        # Neo4j setup (CSV imports, Cypher samples)
├── cerberus-rag/             # Retrieval layer (main.py connects to Neo4j)
├── cerberus-gai-agents/      # User-facing API layer
├── compose.yml               # Compose configuration
├── env.example               # Template for .env
├── smoke.sh                  # End-to-end health test
└── README.md

🔐 Security Notes

.env is excluded by .gitignore. Never commit real credentials.

Use unique Neo4j passwords in production.

When exposed beyond localhost, enable X-API-Key authentication in both services.

🧩 Future Extensions

Integrate STRIDE/DREAD risk ontology into the Neo4j graph.

Add RAG natural-language → Cypher translation (via LLM).

Develop a web dashboard for live DFD visualisation and threat scoring.
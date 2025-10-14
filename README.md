# CERBERUS — AI-Powered Cyber Risk Assessment

End-to-end microservices for cyber threat modelling using **Neo4j + RAG + Agents**.  
The API returns hierarchical graph data: `Project → Diagram → Node → Threat`.

## Architecture

┌───────────────────────────────────────┐
│ cerberus-gai-agents (FastAPI, :8001) │ /ask → proxy to RAG
└───────────────────────────────────────┘
│
▼
┌───────────────────────────────────────┐
│ cerberus-rag (FastAPI, :8002) │ /healthz /readyz /query (/bootstrap)
│ connects to Neo4j via official driver
└───────────────────────────────────────┘
│
▼
┌───────────────────────────────────────┐
│ Neo4j 5.x (Bolt :7687) │
│ Project-[:CONTAINS]->Diagram-[:HAS_NODE]->Node-[:HAS_THREAT]->Threat
└───────────────────────────────────────┘


## Repository Layout

CERBERUS/
├─ cerberus-gai-agents/ # Agents façade (FastAPI)
├─ cerberus-rag/ # RAG / Graph API (FastAPI + Neo4j driver)
├─ cerberus-graph-db/ # Neo4j related assets (optional)
├─ compose.yml # Docker Compose
├─ env.example # Template for .env
└─ README.md


## Prerequisites

- Docker + Docker Compose
- `.env` at the repo root (see `env.example`):
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your_password>
NEO4J_URI=bolt://neo4j:7687
RAG_BASE_URL=http://cerberus-rag:8002
OPENAI_API_KEY=<optional-if-needed>


## Run

```bash
docker compose up -d --build
docker compose ps
Health checks:

bash
Copy code
# Neo4j Browser (web UI)
open http://127.0.0.1:7474  # or just visit in your browser

# RAG
curl -s http://127.0.0.1:8002/healthz | jq .
curl -s http://127.0.0.1:8002/readyz  | jq .

# Agents
curl -s http://127.0.0.1:8001/healthz | jq .
Seed Demo Data
Option A — One-click via HTTP (recommended for teammates)

Copy code
curl -s -X POST http://127.0.0.1:8002/bootstrap | jq .
This creates:

Project proj-1 with Diagram dfd-1

Node n1: Gateway (Threat t1: Spoofing)

Node n2: Database (Threat t2: Tampering)

Option B — Auto-seed in Compose (optional)
Add this one-shot job to compose.yml:

yaml
Copy code
  seed-demo:
    image: curlimages/curl:8.7.1
    depends_on:
      cerberus-rag:
        condition: service_healthy
    command: >
      sh -lc "curl -fsS -X POST http://cerberus-rag:8002/bootstrap || true"
    restart: "no"
    networks: [cerberus-net]
Then simply:


docker compose up -d --build
API
RAG — POST /query (port 8002)
Returns hierarchical projects → diagrams → nodes → threats. Optional project_id filter.

Request

{
  "query": "show hierarchy",
  "project_id": "proj-1",  // optional
  "top_k": 50              // optional, default 50
}
Response (example)


{
  "projects": [
    {
      "project_id": "proj-1",
      "diagrams": [
        {
          "diagram_id": "dfd-1",
          "nodes": [
            {
              "node_id": "n1",
              "name": "Gateway",
              "threats": [{"threat_id":"t1","name":"Spoofing"}]
            },
            {
              "node_id": "n2",
              "name": "Database",
              "threats": [{"threat_id":"t2","name":"Tampering"}]
            }
          ]
        }
      ]
    }
  ],
  "answer": "hierarchical data retrieved",
  "hint": "schema = Project-[:CONTAINS]->Diagram-[:HAS_NODE]->Node-[:HAS_THREAT]->Threat"
}
cURL


curl -s -X POST http://127.0.0.1:8002/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"show hierarchy","project_id":"proj-1","top_k":50}' | jq .
Agents — POST /ask (port 8001)
Forwards to RAG. Example:


curl -s -X POST http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"show hierarchy","project_id":"proj-1","top_k":50}' | jq .
Troubleshooting
Merge conflict markers in README
If you see <<<<<<< HEAD, =======, >>>>>>>, resolve conflicts and keep this clean version.

projects: []
Seed the data: POST /bootstrap or enable the compose auto-seed job.

/readyz is Not Found
RAG container isn’t on the latest code: docker compose up -d --build cerberus-rag.

Git push permission denied (publickey)
Use HTTPS + PAT or add an SSH key to GitHub.

Development
Rebuild one service: docker compose up -d --build cerberus-rag

Tail logs: docker logs -f cerberus-suite-cerberus-rag-1

Tear down: docker compose down

License
MIT (or your team’s policy)


### Optional: minimal `.gitignore` and `env.example`

**`.gitignore`**
```gitignore
# Python
__pycache__/
*.pyc
.venv/
.env

# Neo4j local data & logs (we use docker volumes)
neo4j_data/
neo4j_logs/

# OS / IDE
.DS_Store
.idea/
.vscode/
env.example

makefile
Copy code
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4j_password_here
NEO4J_URI=bolt://neo4j:7687
RAG_BASE_URL=http://cerberus-rag:8002
OPENAI_API_KEY=

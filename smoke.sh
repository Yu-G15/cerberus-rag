#!/usr/bin/env bash
set -euo pipefail
echo "== Neo4j =="
curl -fsS http://127.0.0.1:7474 > /dev/null && echo "Neo4j UI OK"

echo "== RAG =="
curl -fsS http://127.0.0.1:8002/healthz && echo
curl -fsS -X POST http://127.0.0.1:8002/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"show components","top_k":1}' | jq .

echo "== Agents =="
curl -fsS http://127.0.0.1:8001/healthz && echo
curl -fsS -X POST http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"show components","top_k":1}' | jq .
echo "All good ✅"


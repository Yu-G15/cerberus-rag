Cerberus Graph DB (Neo4j)

This folder contains the Neo4j graph database setup for the Cerberus 
security platform, including:
- `docker-compose.yaml` to run Neo4j 5.x locally via Docker
- `neo4j_import/` with CSVs for nodes, relationships and joins
- optional `queries/` with Cypher queries to create constraints and 
analyze the graph

Quick Start

1) Prerequisites
- Docker & Docker Compose
- macOS / Linux / Windows with WSL2
- ~2GB RAM available

2) Start Neo4j
From the repository root:

cd graph-db
docker compose up -d
Neo4j will be available at:
Browser: http://localhost:7474
Bolt: bolt://localhost:7687
Default credentials (change in production):
user: neo4j
pass: password1

3) Import Data (CSV)
The neo4j_import/ directory is mounted into the container as 
/var/lib/neo4j/import.
In Neo4j Browser, run e.g.:
// sanity check
LOAD CSV WITH HEADERS FROM 'file:///components.csv' AS row
RETURN row LIMIT 3;

Then create nodes:
// DFD nodes (Process / ExternalEntity / DataStore rows are included in 
the CSV)
LOAD CSV WITH HEADERS FROM 'file:///components.csv' AS row
CREATE (n:DFDNode {
  key: row.key,
  name: row.name,
  description: row.description,
  dfd_level: toInteger(row.dfd_level),
  zone: row.zone,
  owner: row.owner,
  criticality: row.criticality,
  pos_x: toFloat(row.pos_x),
  pos_y: toFloat(row.pos_y),
  width: toFloat(row.width),
  height: toFloat(row.height),
  type: row.type
});

Relationships:
// Data flows
LOAD CSV WITH HEADERS FROM 'file:///data_flows.csv' AS row
MATCH (src:DFDNode {key: row.from_key})
MATCH (dst:DFDNode {key: row.to_key})
CREATE (src)-[:DATA_FLOW {
  label: row.label,
  description: row.description,
  protocol: row.protocol,
  method: row.method,
  payload_schema: row.payload_schema,
  frequency: row.frequency,
  pii: row.pii = '1' OR toLower(row.pii) = 'true',
  confidentiality: row.confidentiality,
  integrity: row.integrity,
  availability: row.availability,
  auth_required: row.auth_required = '1' OR toLower(row.auth_required) = 
'true',
  encryption_in_transit: row.encryption_in_transit = '1' OR 
toLower(row.encryption_in_transit) = 'true'
}]->(dst);

Threats & joins:
// Threat nodes
LOAD CSV WITH HEADERS FROM 'file:///threats.csv' AS row
CREATE (t:ThreatNode {
  key: row.key,
  name: row.name,
  threat_type: row.threat_type,
  criticality: row.criticality,
  status: row.status
});

// Threat → Component
LOAD CSV WITH HEADERS FROM 'file:///threatens.csv' AS row
MATCH (t:ThreatNode {key: row.threat_key})
MATCH (c:DFDNode    {key: row.component_key})
MERGE (t)-[:THREATENS]->(c);

// Diagrams
LOAD CSV WITH HEADERS FROM 'file:///diagrams.csv' AS row
CREATE (d:Diagram { key: row.key, name: row.name });

// Diagram → Element / Threat
LOAD CSV WITH HEADERS FROM 'file:///has_element.csv' AS row
MATCH (d:Diagram {key: row.diagram_key})
MATCH (c:DFDNode {key: row.component_key})
MERGE (d)-[:HAS_ELEMENT]->(c);

LOAD CSV WITH HEADERS FROM 'file:///has_threat.csv' AS row
MATCH (d:Diagram {key: row.diagram_key})
MATCH (t:ThreatNode {key: row.threat_key})
MERGE (d)-[:HAS_THREAT]->(t);

// Trust Boundaries
LOAD CSV WITH HEADERS FROM 'file:///trust_boundaries.csv' AS row
CREATE (tb:TrustBoundaryNode {
  key: row.key,
  name: row.name,
  boundary_type: row.boundary_type,
  criticality: row.criticality,
  description: row.description
});

LOAD CSV WITH HEADERS FROM 'file:///has_trust_boundary.csv' AS row
MATCH (tb:TrustBoundaryNode {key: row.boundary_key})
MATCH (c:DFDNode            {key: row.component_key})
MERGE (tb)-[:PROTECTS]->(c);

4) Constraints / Indexes
CREATE CONSTRAINT threatnode_key  IF NOT EXISTS FOR (n:ThreatNode)         
REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT dfdnode_key     IF NOT EXISTS FOR (n:DFDNode)            
REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT diagram_key     IF NOT EXISTS FOR (n:Diagram)            
REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT trustboundary_key IF NOT EXISTS FOR 
(n:TrustBoundaryNode) REQUIRE n.key IS UNIQUE;

5) Example Queries
Boundary-crossing flows for one diagram:
MATCH (d:Diagram {key: 
'dg_admin_portal_0101'})-[:HAS_ELEMENT]->(s:DFDNode)
MATCH (s)-[f:DATA_FLOW]->(t:DFDNode)
MATCH (tb1:TrustBoundaryNode)-[:PROTECTS]->(s)
MATCH (tb2:TrustBoundaryNode)-[:PROTECTS]->(t)
WHERE tb1.key <> tb2.key
RETURN
  f.label   AS flow,
  s.name    AS from,  tb1.name AS from_boundary,
  t.name    AS to,    tb2.name AS to_boundary,
  f.protocol AS protocol,
  f.pii       AS PII,
  f.confidentiality AS C,
  f.encryption_in_transit AS TLS
ORDER BY C DESC, PII DESC;

Counts:
MATCH (n:Diagram)            RETURN "Diagram"            AS type, count(n) 
AS total
UNION ALL
MATCH (n:DFDNode)            RETURN "DFDNode",                  count(n)
UNION ALL
MATCH (n:ThreatNode)         RETURN "ThreatNode",               count(n)
UNION ALL
MATCH (n:TrustBoundaryNode)  RETURN "TrustBoundaryNode",        count(n)
UNION ALL
MATCH ()-[r:DATA_FLOW]->()   RETURN "DATA_FLOW",                count(r)
UNION ALL
MATCH ()-[r:HAS_ELEMENT]->() RETURN "HAS_ELEMENT",              count(r)
UNION ALL
MATCH ()-[r:HAS_THREAT]->()  RETURN "HAS_THREAT",               count(r)
UNION ALL
MATCH ()-[r:THREATENS]->()   RETURN "THREATENS",                count(r);

6) Stop / Clean
docker compose down


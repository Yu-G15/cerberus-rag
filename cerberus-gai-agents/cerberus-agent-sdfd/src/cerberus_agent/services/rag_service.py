import os
from typing import Dict, Any, List, Optional, TypedDict, Literal
from datetime import datetime

import structlog
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Neo4jVector
from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain, RetrievalQA
from langchain.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, END
from neo4j import GraphDatabase

from cerberus_agent.core.config import Settings

logger = structlog.get_logger(__name__)


class GraphState(TypedDict):
    question: str
    route: Optional[str]
    subqueries: Optional[List[str]]
    documents: Optional[List[Dict[str, Any]]]
    context: Optional[str]
    prompt_with_context: Optional[str]
    cypher_query: Optional[str]
    graph_results: Optional[Any]
    final_answer: Optional[str]
    metadata: Optional[Dict[str, Any]]


class RouteQuery(BaseModel):
    datasource: Literal["vector_search", "graph_query"] = Field(
        ...,
        description="Choose which datasource is most relevant for answering the question"
    )


class SubQuery(BaseModel):
    sub_query: str = Field(
        ...,
        description="A specific sub-question that helps answer the main question"
    )


class SubQueries(BaseModel):
    queries: List[SubQuery] = Field(
        ...,
        description="List of sub-queries to answer the main question"
    )


class RAGService:
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_pass = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(
            self.neo4j_uri, 
            auth=(self.neo4j_user, self.neo4j_pass)
        )
        
        self.neo4j_graph = Neo4jGraph(
            url=self.neo4j_uri,
            username=self.neo4j_user,
            password=self.neo4j_pass
        )
        
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        self.index_name = os.getenv("VECTOR_INDEX_NAME", "idx_chunks")
        self.node_label = os.getenv("VECTOR_NODE_LABEL", "Chunk")
        
        self.workflow = self._build_workflow()
        
        logger.info(
            "RAG Service initialized",
            neo4j_uri=self.neo4j_uri,
            model=settings.OPENAI_MODEL
        )
    
    def close(self):
        if self.driver:
            self.driver.close()
        logger.info("RAG Service closed")
    
    def route_question(self, state: GraphState) -> GraphState:
        logger.info("Routing question")
        question = state["question"]
        
        system_prompt = """You are an expert at routing user questions.
        
Route to:
- 'vector_search': For semantic search and conceptual questions
- 'graph_query': For structured queries about relationships and data
"""
        
        route_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])
        
        structured_llm = self.llm.with_structured_output(RouteQuery)
        router = route_prompt | structured_llm
        
        try:
            result = router.invoke({"question": question})
            route = result.datasource
            
            logger.info(f"Routed to: {route}", question=question[:100])
            
            return {
                **state,
                "route": route,
                "metadata": {
                    **(state.get("metadata") or {}),
                    "routing_decision": route,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            logger.error("Routing failed", error=str(e))
            return {**state, "route": "vector_search"}
    
    def decompose_query(self, state: GraphState) -> GraphState:
        logger.info("Decomposing query")
        question = state["question"]
        
        system_message = """Break down complex questions into 2-4 simpler sub-questions.
Each sub-question should be specific, focused, and answerable independently."""
        
        decompose_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "Question: {question}")
        ])
        
        structured_llm = self.llm.with_structured_output(SubQueries)
        decomposer = decompose_prompt | structured_llm
        
        try:
            result = decomposer.invoke({"question": question})
            subqueries = [sq.sub_query for sq in result.queries]
            
            logger.info(
                "Query decomposed",
                subqueries_count=len(subqueries)
            )
            
            return {**state, "subqueries": subqueries}
        except Exception as e:
            logger.error("Query decomposition failed", error=str(e))
            return {**state, "subqueries": [question]}
    
    def vector_search(self, state: GraphState) -> GraphState:
        logger.info("Executing vector search")
        question = state["question"]
        subqueries = state.get("subqueries", [question])
        
        try:
            vector_store = Neo4jVector.from_existing_graph(
                embedding=self.embeddings,
                url=self.neo4j_uri,
                username=self.neo4j_user,
                password=self.neo4j_pass,
                index_name=self.index_name,
                node_label=self.node_label,
                text_node_properties=["text"]
            )
            
            retrieval_qa = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=vector_store.as_retriever(search_kwargs={"k": 5})
            )
            
            all_results = []
            for subquery in subqueries:
                result = retrieval_qa.invoke({"query": subquery})
                all_results.append({
                    "query": subquery,
                    "result": result.get("result", "")
                })
            
            context = "\n\n".join([
                f"Query: {r['query']}\nAnswer: {r['result']}"
                for r in all_results
            ])
            
            logger.info("Vector search completed", results_count=len(all_results))
            
            return {
                **state,
                "documents": all_results,
                "context": context
            }
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e), exc_info=True)
            return {
                **state,
                "documents": [],
                "context": f"Error: {str(e)}"
            }
    
    def graph_query(self, state: GraphState) -> GraphState:
        logger.info("Executing graph query")
        question = state["question"]
        
        try:
            cypher_chain = GraphCypherQAChain.from_llm(
                llm=self.llm,
                graph=self.neo4j_graph,
                verbose=True,
                return_intermediate_steps=True,
                allow_dangerous_requests=True
            )
            
            result = cypher_chain.invoke({"query": question})
            
            intermediate_steps = result.get("intermediate_steps", [])
            cypher_query = intermediate_steps[0] if intermediate_steps else None
            
            logger.info("Graph query completed", cypher_query=cypher_query)
            
            return {
                **state,
                "cypher_query": cypher_query,
                "graph_results": result.get("result", ""),
                "final_answer": result.get("result", "")
            }
            
        except Exception as e:
            logger.error("Graph query failed", error=str(e), exc_info=True)
            return {
                **state,
                "graph_results": f"Error: {str(e)}",
                "final_answer": f"Error querying graph: {str(e)}"
            }
    
    def augment_prompt_with_context(self, state: GraphState) -> GraphState:
        logger.info("Augmenting prompt with context")
        question = state["question"]
        context = state.get("context", "")
        
        if not context:
            logger.warning("No context available")
            return {**state, "prompt_with_context": question}
        
        augmented_prompt = f"""Based on the context below, answer the question.

CONTEXT:
{context}

QUESTION: {question}

Provide a comprehensive answer based on the context."""
        
        logger.info("Prompt augmented")
        
        return {**state, "prompt_with_context": augmented_prompt}
    
    def generate_final_answer(self, state: GraphState) -> GraphState:
        logger.info("Generating final answer")
        prompt = state.get("prompt_with_context") or state["question"]
        
        try:
            response = self.llm.invoke(prompt)
            final_answer = response.content
            
            logger.info("Answer generated")
            
            return {**state, "final_answer": final_answer}
            
        except Exception as e:
            logger.error("Answer generation failed", error=str(e))
            return {**state, "final_answer": f"Error: {str(e)}"}
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        
        workflow.add_node("route_question", self.route_question)
        workflow.add_node("decompose_query", self.decompose_query)
        workflow.add_node("vector_search", self.vector_search)
        workflow.add_node("graph_query", self.graph_query)
        workflow.add_node("augment_prompt", self.augment_prompt_with_context)
        workflow.add_node("generate_answer", self.generate_final_answer)
        
        workflow.set_entry_point("route_question")
        
        workflow.add_conditional_edges(
            "route_question",
            lambda state: state["route"],
            {
                "vector_search": "decompose_query",
                "graph_query": "graph_query"
            }
        )
        
        workflow.add_edge("decompose_query", "vector_search")
        workflow.add_edge("vector_search", "augment_prompt")
        workflow.add_edge("augment_prompt", "generate_answer")
        workflow.add_edge("generate_answer", END)
        workflow.add_edge("graph_query", END)
        
        return workflow.compile()
    
    async def query(
        self,
        question: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        logger.info("Starting workflow", question=question[:100])
        
        initial_state: GraphState = {
            "question": question,
            "route": None,
            "subqueries": None,
            "documents": None,
            "context": None,
            "prompt_with_context": None,
            "cypher_query": None,
            "graph_results": None,
            "final_answer": None,
            "metadata": metadata or {}
        }
        
        try:
            final_state = self.workflow.invoke(initial_state)
            
            logger.info(
                "Workflow completed",
                route=final_state.get("route"),
                has_answer=bool(final_state.get("final_answer"))
            )
            
            return final_state
            
        except Exception as e:
            logger.error("Workflow failed", error=str(e), exc_info=True)
            return {
                **initial_state,
                "final_answer": f"Error: {str(e)}",
                "metadata": {**(metadata or {}), "error": str(e)}
            }
    
    async def search_documents(
        self,
        query: str,
        k: int = 8,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            logger.info("Vector search", query=query[:100], k=k)
            
            vector_store = Neo4jVector.from_existing_graph(
                embedding=self.embeddings,
                url=self.neo4j_uri,
                username=self.neo4j_user,
                password=self.neo4j_pass,
                index_name=self.index_name,
                node_label=self.node_label,
                text_node_properties=["text"]
            )
            
            docs_with_scores = vector_store.similarity_search_with_score(query, k=k)
            
            results = []
            for doc, score in docs_with_scores:
                if score_threshold and score < score_threshold:
                    continue
                
                result = {
                    "content": doc.page_content[:2000],
                    "score": float(score),
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown"),
                    "node_id": doc.metadata.get("node_id"),
                }
                
                if filters and not self._matches_filters(result["metadata"], filters):
                    continue
                
                results.append(result)
            
            logger.info("Search completed", results_count=len(results))
            return results
            
        except Exception as e:
            logger.error("Search failed", error=str(e), exc_info=True)
            return []
    
    def _matches_filters(
        self, 
        metadata: Dict[str, Any], 
        filters: Dict[str, Any]
    ) -> bool:
        for key, value in filters.items():
            if metadata.get(key) != value:
                return False
        return True
    
    async def search_with_routing(
        self,
        question: str,
        force_route: Optional[Literal["vector_search", "graph_query"]] = None
    ) -> Dict[str, Any]:
        if force_route:
            logger.info(f"Forcing route: {force_route}")
            
            if force_route == "graph_query":
                state = {"question": question}
                return self.graph_query(state)
            else:
                state = {"question": question, "subqueries": [question]}
                return self.vector_search(state)
        
        return await self.query(question)
    
    async def search_dfd_nodes(
        self,
        project_id: str,
        diagram_id: str,
        search_query: Optional[str] = None,
        k: int = 10
    ) -> Dict[str, Any]:
        logger.info(
            "Searching DFD nodes",
            project_id=project_id,
            diagram_id=diagram_id
        )
        
        try:
            with self.driver.session() as session:
                if search_query:
                    logger.info("Using semantic search")
                    query_embedding = self.embeddings.embed_query(search_query)
                    
                    query = """
                    MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
                    MATCH (d)-[:HAS_ELEMENT]->(comp)
                    WITH comp, comp.name + ' ' + coalesce(comp.description, '') as text
                    RETURN 
                        comp.uid as id,
                        comp.name as name,
                        labels(comp) as labels,
                        comp.description as description,
                        comp.criticality as criticality,
                        comp.zone as zone,
                        comp.owner as owner,
                        comp.technology as technology,
                        comp.pos_x as pos_x,
                        comp.pos_y as pos_y,
                        properties(comp) as properties
                    LIMIT $k
                    """
                    
                    result = session.run(query, project_id=project_id, diagram_id=diagram_id, k=k)
                else:
                    logger.info("Retrieving all nodes")
                    
                    query = """
                    MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
                    MATCH (d)-[:HAS_ELEMENT]->(comp)
                    RETURN 
                        comp.uid as id,
                        comp.name as name,
                        labels(comp) as labels,
                        comp.description as description,
                        comp.criticality as criticality,
                        comp.zone as zone,
                        comp.owner as owner,
                        comp.technology as technology,
                        comp.pos_x as pos_x,
                        comp.pos_y as pos_y,
                        properties(comp) as properties
                    ORDER BY comp.name
                    """
                    
                    result = session.run(query, project_id=project_id, diagram_id=diagram_id)
                
                nodes = [dict(record) for record in result]
                connections = await self._get_dfd_connections(project_id, diagram_id)
                
                logger.info(
                    "DFD nodes retrieved",
                    nodes_count=len(nodes),
                    connections_count=len(connections)
                )
                
                return {
                    "nodes": nodes,
                    "connections": connections,
                    "metadata": {
                        "project_id": project_id,
                        "diagram_id": diagram_id,
                        "search_query": search_query,
                        "total_nodes": len(nodes)
                    }
                }
                
        except Exception as e:
            logger.error("DFD search failed", error=str(e), exc_info=True)
            return {
                "nodes": [],
                "connections": [],
                "metadata": {"error": str(e)}
            }
    
    async def _get_dfd_connections(
        self,
        project_id: str,
        diagram_id: str
    ) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
                MATCH (d)-[:HAS_ELEMENT]->(source)
                MATCH (source)-[r:DATA_FLOW]->(target)
                RETURN 
                    r.uid as id,
                    source.uid as from_component,
                    source.name as from_name,
                    target.uid as to_component,
                    target.name as to_name,
                    r.label as label,
                    r.protocol as protocol,
                    r.auth_required as auth_required,
                    r.encryption_in_transit as encryption_in_transit,
                    r.pii as pii,
                    r.confidentiality as confidentiality,
                    properties(r) as properties
                ORDER BY r.label
                """
                
                result = session.run(query, project_id=project_id, diagram_id=diagram_id)
                return [dict(record) for record in result]
                
        except Exception as e:
            logger.error("Failed to get connections", error=str(e))
            return []
    
    async def analyze_threats_with_llm(
        self,
        dfd_data: Dict[str, Any],
        analysis_depth: str = "comprehensive"
    ) -> List[Dict[str, Any]]:
        logger.info("Analyzing threats", analysis_depth=analysis_depth)
        
        nodes = dfd_data.get("nodes", [])
        connections = dfd_data.get("connections", [])
        
        if not nodes:
            logger.warning("No nodes to analyze")
            return []
        
        try:
            context = self._build_threat_analysis_context(nodes, connections)
            
            prompt = f"""You are a cybersecurity expert performing STRIDE threat modeling.

CRITICAL: Respond with ONLY valid JSON array.

DIAGRAM CONTEXT:
{context}

ANALYSIS DEPTH: {analysis_depth}

Use STRIDE methodology:
- Spoofing, Tampering, Repudiation
- Information Disclosure, Denial of Service
- Elevation of Privilege

Focus on realistic threats based on actual components and flows.

RESPONSE FORMAT (JSON ARRAY ONLY):
[
  {{
    "threat_id": "unique_id",
    "threat_name": "Name",
    "threat_type": "spoofing|tampering|repudiation|information_disclosure|denial_of_service|elevation_of_privilege",
    "description": "Detailed description",
    "linked_component_ids": ["id1", "id2"],
    "criticality": "low|medium|high|critical",
    "impact": "Impact description",
    "likelihood": "low|medium|high",
    "mitigation_strategies": ["strategy1", "strategy2"],
    "confidence_score": 0.0-1.0
  }}
]

Identify 5-10 contextually relevant threats."""
            
            response = self.llm.invoke(prompt)
            threats = self._parse_threat_response(response.content, nodes, connections)
            
            if analysis_depth == "basic":
                threats = [t for t in threats if t.get("criticality") in ["high", "critical"]]
            elif analysis_depth == "standard":
                threats = [t for t in threats if t.get("criticality") in ["medium", "high", "critical"]]
            
            logger.info("Analysis completed", total_threats=len(threats))
            return threats
            
        except Exception as e:
            logger.error("Threat analysis failed", error=str(e), exc_info=True)
            return []
    
    def _build_threat_analysis_context(
        self,
        nodes: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> str:
        context = "COMPONENTS:\n\n"
        
        for node in nodes:
            node_type = node.get("labels", ["Unknown"])[0] if node.get("labels") else "Unknown"
            context += f"- {node.get('name', 'Unknown')} ({node_type})\n"
            
            if node.get('description'):
                context += f"  Description: {node['description']}\n"
            if node.get('criticality'):
                context += f"  Criticality: {node['criticality']}\n"
            if node.get('technology'):
                context += f"  Technology: {node['technology']}\n"
        
        if connections:
            context += "\nDATA FLOWS:\n\n"
            for conn in connections:
                context += f"- {conn.get('from_name', 'Unknown')} → {conn.get('to_name', 'Unknown')}\n"
                
                if conn.get('label'):
                    context += f"  Label: {conn['label']}\n"
                if conn.get('protocol'):
                    context += f"  Protocol: {conn['protocol']}\n"
                if conn.get('pii'):
                    context += f"  Contains PII: Yes\n"
                if conn.get('confidentiality'):
                    context += f"  Confidentiality: {conn['confidentiality']}\n"
                if conn.get('encryption_in_transit') is False:
                    context += f"  ⚠️ No encryption\n"
        
        return context
    
    def _parse_threat_response(
        self,
        response_text: str,
        nodes: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        import json
        import re
        
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            try:
                threats = json.loads(cleaned)
                if isinstance(threats, list):
                    logger.info("Parsed threats", count=len(threats))
                    return self._validate_threats(threats, nodes, connections)
            except json.JSONDecodeError:
                pass
            
            json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if json_match:
                threats = json.loads(json_match.group(0))
                logger.info("Extracted threats", count=len(threats))
                return self._validate_threats(threats, nodes, connections)
            
            logger.warning("Could not parse response")
            return []
            
        except Exception as e:
            logger.error("Parse failed", error=str(e))
            return []
    
    def _validate_threats(
        self,
        threats: List[Dict[str, Any]],
        nodes: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        valid_threats = []
        required = ["threat_id", "threat_name", "threat_type", "description", "criticality"]
        valid_types = [
            "spoofing", "tampering", "repudiation", 
            "information_disclosure", "denial_of_service", 
            "elevation_of_privilege"
        ]
        valid_crit = ["low", "medium", "high", "critical"]
        
        for threat in threats:
            if not all(field in threat and threat[field] for field in required):
                continue
            
            if threat["threat_type"] not in valid_types:
                continue
            
            if threat["criticality"] not in valid_crit:
                continue
            
            valid_threats.append(threat)
        
        logger.info(
            "Validation completed",
            total=len(threats),
            valid=len(valid_threats)
        )
        
        return valid_threats
    
    async def search_threat_intelligence(
        self,
        threat_query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        logger.info("Searching threat intelligence", query=threat_query[:100])
        enhanced = f"security threat vulnerability attack: {threat_query}"
        return await self.search_documents(query=enhanced, k=k, score_threshold=0.7)
    
    async def get_statistics(self) -> Dict[str, Any]:
        try:
            with self.driver.session() as session:
                node_result = session.run("MATCH (n) RETURN count(n) as total")
                total_nodes = node_result.single()["total"]
                
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
                total_rels = rel_result.single()["total"]
                
                chunk_result = session.run(f"MATCH (c:{self.node_label}) RETURN count(c) as total")
                total_chunks = chunk_result.single()["total"]
                
                return {
                    "neo4j_uri": self.neo4j_uri,
                    "total_nodes": total_nodes,
                    "total_relationships": total_rels,
                    "total_chunks": total_chunks,
                    "index_name": self.index_name,
                    "workflow_type": "LangGraph GraphRAG",
                    "routing_enabled": True,
                    "decomposition_enabled": True
                }
                
        except Exception as e:
            logger.error("Statistics failed", error=str(e))
            return {
                "error": str(e),
                "total_chunks": 0,
                "workflow_type": "LangGraph GraphRAG"
            }
    
    async def index_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Dict[str, Any]:
        try:
            logger.info("Indexing document", length=len(content))
            
            chunks = self._chunk_text(content, chunk_size, chunk_overlap)
            
            with self.driver.session() as session:
                for i, chunk in enumerate(chunks):
                    embedding = self.embeddings.embed_query(chunk)
                    
                    chunk_meta = {
                        **metadata,
                        "chunk_index": i,
                        "chunk_count": len(chunks),
                        "indexed_at": datetime.utcnow().isoformat()
                    }
                    
                    session.run(
                        f"""
                        CREATE (c:{self.node_label})
                        SET c.text = $text,
                            c.embedding = $embedding,
                            c.metadata = $metadata,
                            c.indexed_at = datetime()
                        """,
                        text=chunk,
                        embedding=embedding,
                        metadata=chunk_meta
                    )
            
            logger.info("Document indexed", chunks=len(chunks))
            
            return {
                "success": True,
                "chunks_created": len(chunks),
                "total_length": len(content),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error("Indexing failed", error=str(e), exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _chunk_text(
        self, 
        text: str, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ) -> List[str]:
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - chunk_overlap
        
        return chunks

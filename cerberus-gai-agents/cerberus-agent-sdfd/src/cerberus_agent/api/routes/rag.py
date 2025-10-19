import uuid
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from cerberus_agent.core.config import Settings, get_settings
from cerberus_agent.services.rag_service import RAGService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


class GraphRAGQueryRequest(BaseModel):
    question: str = Field(..., description="User question to answer")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class GraphRAGQueryResponse(BaseModel):
    question: str = Field(..., description="Original question")
    final_answer: str = Field(..., description="Final answer")
    route: Optional[str] = Field(..., description="Route taken")
    subqueries: Optional[list] = Field(default=None, description="Decomposed subqueries")
    cypher_query: Optional[str] = Field(default=None, description="Generated Cypher query")
    context: Optional[str] = Field(default=None, description="Retrieved context")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Workflow metadata")
    query_id: str = Field(..., description="Unique query ID")
    timestamp: str = Field(..., description="Query timestamp")


class RoutedSearchRequest(BaseModel):
    question: str = Field(..., description="User question")
    force_route: Optional[Literal["vector_search", "graph_query"]] = Field(
        default=None,
        description="Force a specific route"
    )


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    k: int = Field(default=8, ge=1, le=50, description="Number of results")
    score_threshold: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Minimum similarity score"
    )
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class SearchResult(BaseModel):
    content: str = Field(..., description="Document content")
    score: float = Field(..., description="Similarity score")
    source: str = Field(..., description="Source identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    node_id: Optional[str] = Field(default=None, description="Neo4j node ID")


class SearchResponse(BaseModel):
    results: List[SearchResult] = Field(..., description="Search results")
    query: str = Field(..., description="Original query")
    results_count: int = Field(..., description="Number of results")
    search_id: str = Field(..., description="Unique search ID")
    timestamp: str = Field(..., description="Search timestamp")


class DiagramContextRequest(BaseModel):
    query: str = Field(..., description="Search query")
    project_id: Optional[str] = Field(default=None, description="Project ID filter")
    diagram_id: Optional[str] = Field(default=None, description="Diagram ID filter")
    k: int = Field(default=5, ge=1, le=20, description="Number of results")


class ThreatIntelRequest(BaseModel):
    threat_query: str = Field(..., description="Threat-related query")
    k: int = Field(default=5, ge=1, le=20, description="Number of results")


class AugmentPromptRequest(BaseModel):
    query: str = Field(..., description="User query to augment")
    context_sources: Optional[List[str]] = Field(default=None, description="Context sources")
    max_context_length: int = Field(
        default=2000, 
        ge=500, 
        le=8000, 
        description="Maximum context length"
    )
    k: int = Field(default=5, ge=1, le=20, description="Number of documents")


class AugmentPromptResponse(BaseModel):
    augmented_prompt: str = Field(..., description="Augmented prompt")
    retrieved_contexts: List[SearchResult] = Field(..., description="Retrieved contexts")
    context_used: bool = Field(..., description="Whether context was used")
    contexts_count: int = Field(..., description="Number of contexts used")


class IndexDocumentRequest(BaseModel):
    content: str = Field(..., description="Document content to index")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    chunk_size: int = Field(default=1000, ge=100, le=5000, description="Chunk size")
    chunk_overlap: int = Field(default=200, ge=0, le=1000, description="Chunk overlap")


class IndexDocumentResponse(BaseModel):
    success: bool = Field(..., description="Whether indexing succeeded")
    chunks_created: int = Field(..., description="Number of chunks created")
    total_length: int = Field(..., description="Total document length")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")


class RAGStatisticsResponse(BaseModel):
    total_chunks: int = Field(..., description="Total indexed chunks")
    index_name: str = Field(..., description="Vector index name")
    index_exists: bool = Field(..., description="Whether index exists")
    node_label: str = Field(..., description="Neo4j node label")
    neo4j_uri: str = Field(..., description="Neo4j connection URI")


class DFDNodesRequest(BaseModel):
    project_id: str = Field(..., description="Project ID")
    diagram_id: str = Field(..., description="Diagram ID")
    search_query: Optional[str] = Field(default=None, description="Semantic search query")
    k: int = Field(default=10, ge=1, le=50, description="Number of results")


class DFDNodesResponse(BaseModel):
    nodes: List[Dict[str, Any]] = Field(..., description="DFD nodes")
    connections: List[Dict[str, Any]] = Field(..., description="Connections")
    metadata: Dict[str, Any] = Field(..., description="Metadata")


class ThreatAnalysisRequest(BaseModel):
    project_id: str = Field(..., description="Project ID")
    diagram_id: str = Field(..., description="Diagram ID")
    analysis_depth: str = Field(
        default="comprehensive", 
        description="Analysis depth (basic, standard, comprehensive)"
    )


class ThreatAnalysisResponse(BaseModel):
    threats: List[Dict[str, Any]] = Field(..., description="Identified threats")
    dfd_data: Dict[str, Any] = Field(..., description="DFD data analyzed")
    analysis_depth: str = Field(..., description="Analysis depth used")
    total_threats: int = Field(..., description="Total threats found")
    timestamp: str = Field(..., description="Analysis timestamp")


@router.post("/query", response_model=GraphRAGQueryResponse)
async def graphrag_query(
    request: GraphRAGQueryRequest,
    settings: Settings = Depends(get_settings)
) -> GraphRAGQueryResponse:
    try:
        logger.info("GraphRAG query", question=request.question[:100])
        
        rag_service = RAGService(settings)
        
        try:
            result = await rag_service.query(
                question=request.question,
                metadata=request.metadata
            )
            
            return GraphRAGQueryResponse(
                question=result["question"],
                final_answer=result.get("final_answer", "No answer generated"),
                route=result.get("route"),
                subqueries=result.get("subqueries"),
                cypher_query=result.get("cypher_query"),
                context=result.get("context"),
                metadata=result.get("metadata"),
                query_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat()
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("GraphRAG query failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"GraphRAG query failed: {str(e)}")


@router.post("/search-with-routing", response_model=GraphRAGQueryResponse)
async def search_with_routing(
    request: RoutedSearchRequest,
    settings: Settings = Depends(get_settings)
) -> GraphRAGQueryResponse:
    try:
        logger.info(
            "Routed search",
            question=request.question[:100],
            force_route=request.force_route
        )
        
        rag_service = RAGService(settings)
        
        try:
            result = await rag_service.search_with_routing(
                question=request.question,
                force_route=request.force_route
            )
            
            return GraphRAGQueryResponse(
                question=result.get("question", request.question),
                final_answer=result.get("final_answer", result.get("graph_results", "No answer")),
                route=result.get("route", request.force_route),
                subqueries=result.get("subqueries"),
                cypher_query=result.get("cypher_query"),
                context=result.get("context"),
                metadata=result.get("metadata", {}),
                query_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat()
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Routed search failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Routed search failed: {str(e)}")


@router.get("/workflow-info")
async def get_workflow_info() -> Dict[str, Any]:
    return {
        "workflow_type": "LangGraph GraphRAG",
        "implementation_reference": "https://neo4j.com/blog/developer/neo4j-graphrag-workflow-langchain-langgraph/",
        "features": {
            "intelligent_routing": True,
            "query_decomposition": True,
            "vector_search": True,
            "graph_cypher_qa": True,
            "dynamic_prompting": True,
            "state_management": True
        },
        "workflow_nodes": [
            "route_question",
            "decompose_query",
            "vector_search",
            "graph_query",
            "augment_prompt",
            "generate_answer"
        ],
        "routes": {
            "vector_search": "Semantic search and conceptual questions",
            "graph_query": "Structured queries about relationships"
        },
        "state_attributes": [
            "question",
            "route",
            "subqueries",
            "documents",
            "context",
            "prompt_with_context",
            "cypher_query",
            "graph_results",
            "final_answer",
            "metadata"
        ]
    }


@router.post("/dfd/nodes", response_model=DFDNodesResponse)
async def get_dfd_nodes(
    request: DFDNodesRequest,
    settings: Settings = Depends(get_settings)
) -> DFDNodesResponse:
    try:
        logger.info(
            "DFD nodes request",
            project_id=request.project_id,
            diagram_id=request.diagram_id,
            has_query=bool(request.search_query)
        )
        
        rag_service = RAGService(settings)
        
        try:
            result = await rag_service.search_dfd_nodes(
                project_id=request.project_id,
                diagram_id=request.diagram_id,
                search_query=request.search_query,
                k=request.k
            )
            
            return DFDNodesResponse(
                nodes=result.get("nodes", []),
                connections=result.get("connections", []),
                metadata=result.get("metadata", {})
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("DFD nodes retrieval failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"DFD nodes retrieval failed: {str(e)}")


@router.post("/dfd/analyze-threats", response_model=ThreatAnalysisResponse)
async def analyze_dfd_threats(
    request: ThreatAnalysisRequest,
    settings: Settings = Depends(get_settings)
) -> ThreatAnalysisResponse:
    try:
        logger.info(
            "Threat analysis request",
            project_id=request.project_id,
            diagram_id=request.diagram_id,
            analysis_depth=request.analysis_depth
        )
        
        rag_service = RAGService(settings)
        
        try:
            dfd_data = await rag_service.search_dfd_nodes(
                project_id=request.project_id,
                diagram_id=request.diagram_id
            )
            
            threats = await rag_service.analyze_threats_with_llm(
                dfd_data=dfd_data,
                analysis_depth=request.analysis_depth
            )
            
            return ThreatAnalysisResponse(
                threats=threats,
                dfd_data=dfd_data,
                analysis_depth=request.analysis_depth,
                total_threats=len(threats),
                timestamp=datetime.utcnow().isoformat()
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Threat analysis failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Threat analysis failed: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    settings: Settings = Depends(get_settings)
) -> SearchResponse:
    try:
        logger.info("Search request", query=request.query[:100], k=request.k)
        
        rag_service = RAGService(settings)
        
        try:
            results = await rag_service.search_documents(
                query=request.query,
                k=request.k,
                score_threshold=request.score_threshold,
                filters=request.filters
            )
            
            search_results = [
                SearchResult(
                    content=r["content"],
                    score=r["score"],
                    source=r["source"],
                    metadata=r.get("metadata", {}),
                    node_id=r.get("node_id")
                )
                for r in results
            ]
            
            return SearchResponse(
                results=search_results,
                query=request.query,
                results_count=len(search_results),
                search_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat()
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Search failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search/diagram-context", response_model=SearchResponse)
async def search_diagram_context(
    request: DiagramContextRequest,
    settings: Settings = Depends(get_settings)
) -> SearchResponse:
    try:
        logger.info(
            "Diagram context search",
            query=request.query[:100],
            project_id=request.project_id,
            diagram_id=request.diagram_id
        )
        
        rag_service = RAGService(settings)
        
        try:
            results = await rag_service.search_diagram_context(
                query=request.query,
                project_id=request.project_id,
                diagram_id=request.diagram_id,
                k=request.k
            )
            
            search_results = [
                SearchResult(
                    content=r["content"],
                    score=r["score"],
                    source=r["source"],
                    metadata=r.get("metadata", {}),
                    node_id=r.get("node_id")
                )
                for r in results
            ]
            
            return SearchResponse(
                results=search_results,
                query=request.query,
                results_count=len(search_results),
                search_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat()
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Diagram context search failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagram context search failed: {str(e)}")


@router.post("/search/threat-intelligence", response_model=SearchResponse)
async def search_threat_intelligence(
    request: ThreatIntelRequest,
    settings: Settings = Depends(get_settings)
) -> SearchResponse:
    try:
        logger.info("Threat intelligence search", query=request.threat_query[:100])
        
        rag_service = RAGService(settings)
        
        try:
            results = await rag_service.search_threat_intelligence(
                threat_query=request.threat_query,
                k=request.k
            )
            
            search_results = [
                SearchResult(
                    content=r["content"],
                    score=r["score"],
                    source=r["source"],
                    metadata=r.get("metadata", {}),
                    node_id=r.get("node_id")
                )
                for r in results
            ]
            
            return SearchResponse(
                results=search_results,
                query=request.threat_query,
                results_count=len(search_results),
                search_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat()
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Threat intelligence search failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Threat intelligence search failed: {str(e)}")


@router.post("/augment-prompt", response_model=AugmentPromptResponse)
async def augment_prompt(
    request: AugmentPromptRequest,
    settings: Settings = Depends(get_settings)
) -> AugmentPromptResponse:
    try:
        logger.info("Augmenting prompt", query=request.query[:100])
        
        rag_service = RAGService(settings)
        
        try:
            result = await rag_service.augment_prompt_with_context(
                query=request.query,
                context_sources=request.context_sources,
                max_context_length=request.max_context_length,
                k=request.k
            )
            
            retrieved_contexts = [
                SearchResult(
                    content=ctx["content"],
                    score=ctx["score"],
                    source=ctx["source"],
                    metadata=ctx.get("metadata", {}),
                    node_id=ctx.get("node_id")
                )
                for ctx in result.get("retrieved_contexts", [])
            ]
            
            return AugmentPromptResponse(
                augmented_prompt=result["augmented_prompt"],
                retrieved_contexts=retrieved_contexts,
                context_used=result.get("context_used", False),
                contexts_count=result.get("contexts_count", 0)
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Prompt augmentation failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prompt augmentation failed: {str(e)}")


@router.post("/index", response_model=IndexDocumentResponse)
async def index_document(
    request: IndexDocumentRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
) -> IndexDocumentResponse:
    try:
        logger.info(
            "Indexing document",
            content_length=len(request.content),
            metadata=request.metadata
        )
        
        rag_service = RAGService(settings)
        
        try:
            result = await rag_service.index_document(
                content=request.content,
                metadata=request.metadata,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap
            )
            
            if not result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Indexing failed: {result.get('error', 'Unknown error')}"
                )
            
            return IndexDocumentResponse(
                success=result["success"],
                chunks_created=result["chunks_created"],
                total_length=result["total_length"],
                metadata=result["metadata"]
            )
            
        finally:
            rag_service.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document indexing failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {str(e)}")


@router.get("/statistics", response_model=RAGStatisticsResponse)
async def get_statistics(
    settings: Settings = Depends(get_settings)
) -> RAGStatisticsResponse:
    try:
        logger.info("Getting statistics")
        
        rag_service = RAGService(settings)
        
        try:
            stats = await rag_service.get_statistics()
            
            return RAGStatisticsResponse(
                total_chunks=stats.get("total_chunks", 0),
                index_name=stats.get("index_name", "unknown"),
                index_exists=stats.get("index_exists", False),
                node_label=stats.get("node_label", "unknown"),
                neo4j_uri=stats.get("neo4j_uri", "unknown")
            )
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Failed to get statistics", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    try:
        rag_service = RAGService(settings)
        
        try:
            stats = await rag_service.get_statistics()
            
            return {
                "status": "healthy",
                "neo4j_connected": not stats.get("error"),
                "index_exists": stats.get("index_exists", False),
                "total_chunks": stats.get("total_chunks", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            rag_service.close()
            
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

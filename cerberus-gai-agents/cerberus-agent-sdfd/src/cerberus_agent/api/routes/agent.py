"""Agent endpoints for AI interactions."""

import time
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from cerberus_agent.core.config import get_settings
from cerberus_agent.core.config import Settings
from cerberus_agent.services.agent_service import AgentService
from cerberus_agent.services.guardrail_service import GuardrailService

logger = structlog.get_logger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message", min_length=1, max_length=10000)
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    model: Optional[str] = Field(None, description="OpenAI model to use")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: Optional[int] = Field(1000, ge=1, le=4000, description="Maximum tokens in response")
    stream: Optional[bool] = Field(False, description="Enable streaming response")
    tools: Optional[List[str]] = Field(None, description="Available tools for the agent")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Agent response")
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="Message ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_used: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(None, description="Tokens used in generation")
    processing_time: float = Field(..., description="Processing time in seconds")
    guardrail_checks: Dict[str, Any] = Field(default_factory=dict, description="Guardrail check results")


class ConversationHistory(BaseModel):
    """Conversation history model."""
    conversation_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRequest(BaseModel):
    """Tool execution request model."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")
    conversation_id: Optional[str] = Field(None, description="Conversation context")


class ToolExecutionResponse(BaseModel):
    """Tool execution response model."""
    result: Any = Field(..., description="Tool execution result")
    success: bool = Field(..., description="Whether execution was successful")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Execution time in seconds")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
) -> ChatResponse:
    """Chat with the AI agent."""
    try:
        # Initialize services
        agent_service = AgentService(settings)
        guardrail_service = GuardrailService(settings)
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Skip guardrail checks as requested
        guardrail_results = {"safe": True, "checks": "disabled"}
        
        # Process the chat request using the actual agent service
        start_time = time.time()
        
        # Call the agent service to process the chat
        agent_response = await agent_service.process_chat(
            message=request.message,
            conversation_id=conversation_id,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools
        )
        
        processing_time = time.time() - start_time
        
        # Log the interaction
        background_tasks.add_task(
            _log_interaction,
            conversation_id=conversation_id,
            user_message=request.message,
            agent_response=agent_response.get("response", ""),
            processing_time=processing_time,
        )
        
        return ChatResponse(
            response=agent_response.get("response", "Analysis completed"),
            conversation_id=conversation_id,
            message_id=str(uuid.uuid4()),
            model_used=agent_response.get("model_used", "gpt-4"),
            tokens_used=agent_response.get("tokens_used"),
            processing_time=processing_time,
            guardrail_checks=guardrail_results,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat processing failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(
    conversation_id: str,
    settings: Settings = Depends(get_settings)
) -> ConversationHistory:
    """Get conversation history."""
    try:
        agent_service = AgentService(settings)
        conversation = await agent_service.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    settings: Settings = Depends(get_settings)
) -> Dict[str, str]:
    """Delete a conversation."""
    try:
        agent_service = AgentService(settings)
        success = await agent_service.delete_conversation(conversation_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete conversation", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tools/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecutionRequest,
    settings: Settings = Depends(get_settings)
) -> ToolExecutionResponse:
    """Execute a tool."""
    try:
        agent_service = AgentService(settings)
        
        start_time = time.time()
        result = await agent_service.execute_tool(
            tool_name=request.tool_name,
            parameters=request.parameters,
            conversation_id=request.conversation_id,
        )
        execution_time = time.time() - start_time
        
        return ToolExecutionResponse(
            result=result.get("result"),
            success=result.get("success", False),
            error=result.get("error"),
            execution_time=execution_time,
        )
        
    except Exception as e:
        logger.error("Tool execution failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Tool execution failed")


@router.get("/tools")
async def list_available_tools(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """List available tools."""
    try:
        agent_service = AgentService(settings)
        tools = await agent_service.list_tools()
        
        return {
            "tools": tools,
            "count": len(tools),
        }
        
    except Exception as e:
        logger.error("Failed to list tools", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list tools")


async def _log_interaction(
    conversation_id: str,
    user_message: str,
    agent_response: str,
    processing_time: float,
) -> None:
    """Log interaction for analytics and monitoring."""
    logger.info(
        "Chat interaction logged",
        conversation_id=conversation_id,
        user_message_length=len(user_message),
        agent_response_length=len(agent_response),
        processing_time=processing_time,
    )

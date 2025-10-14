"""Agent service for handling AI interactions."""

import json
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

import structlog
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from cerberus_agent.core.config import Settings
from cerberus_agent.services.guardrail_service import GuardrailService

logger = structlog.get_logger(__name__)


class AgentService:
    """Service for handling AI agent interactions."""
    
    def __init__(self, settings: Settings):
        """Initialize the agent service."""
        self.settings = settings
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.chat_model = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.guardrail_service = GuardrailService(settings)
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.available_tools = self._initialize_tools()
        self._custom_system_prompt: Optional[str] = None
    
    def _initialize_tools(self) -> List[Dict[str, Any]]:
        """Initialize available tools for the agent."""
        return [
            {
                "name": "search_web",
                "description": "Search the web for current information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "analyze_data_flow",
                "description": "Analyze data flow diagrams for security issues",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "diagram_data": {
                            "type": "string",
                            "description": "Data flow diagram data"
                        }
                    },
                    "required": ["diagram_data"]
                }
            },
            {
                "name": "generate_report",
                "description": "Generate security assessment report",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "findings": {
                            "type": "array",
                            "description": "Security findings to include in report"
                        }
                    },
                    "required": ["findings"]
                }
            }
        ]
    
    async def process_chat(
        self,
        message: str,
        conversation_id: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Process a chat message and return agent response."""
        try:
            # Get or create conversation
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            # Add user message to conversation
            self.conversations[conversation_id].append({
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            # Prepare messages for OpenAI
            messages = self._prepare_messages(conversation_id)
            
            # Configure model parameters
            model_name = model or self.settings.OPENAI_MODEL
            model_temperature = temperature or self.settings.OPENAI_TEMPERATURE
            model_max_tokens = max_tokens or self.settings.OPENAI_MAX_TOKENS
            
            # Prepare tools for function calling
            available_tools = self._filter_tools(tools) if tools else self.available_tools
            
            # Check if OpenAI API key is properly configured
            if not self.settings.OPENAI_API_KEY or self.settings.OPENAI_API_KEY.startswith('your-'):
                # Return a helpful message when API key is not configured
                return {
                    "response": "I'm a security-focused AI assistant for threat modeling and DFD analysis. However, I need a valid OpenAI API key to provide responses. Please configure your OpenAI API key in the environment variables to enable AI-powered security analysis.\n\nIn the meantime, I can help you with:\n• Threat identification using STRIDE methodology\n• Security recommendations\n• DFD component guidance\n• Trust boundary analysis\n\nPlease set up your OpenAI API key to get personalized security insights!",
                    "analysis": None,
                    "recommendations": [],
                    "hints": [],
                    "metadata": {
                        "confidence": 0.0,
                        "category": "configuration_error",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "model_used": "configuration_required",
                    "tokens_used": 0,
                }
            
            # Call OpenAI API to get actual response
            response = await self.openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=model_temperature,
                max_tokens=model_max_tokens,
            )
            
            # Process response
            assistant_message = response.choices[0].message
            response_content = assistant_message.content or ""
            
            # Handle tool calls if present
            if assistant_message.tool_calls:
                tool_results = await self._execute_tool_calls(
                    assistant_message.tool_calls,
                    conversation_id
                )
                
                # Add tool results to conversation
                for tool_call, result in zip(assistant_message.tool_calls, tool_results):
                    self.conversations[conversation_id].append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": tool_call.id,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                
                # Get final response after tool execution
                final_messages = self._prepare_messages(conversation_id)
                final_response = await self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=final_messages,
                    temperature=model_temperature,
                    max_tokens=model_max_tokens,
                )
                
                response_content = final_response.choices[0].message.content or ""
            
            # Parse response from OpenAI - handle both JSON and plain text
            try:
                parsed_response = json.loads(response_content)
                # Ensure it has the expected structure
                if not isinstance(parsed_response, dict):
                    parsed_response = {"response": response_content}
            except json.JSONDecodeError:
                # If not valid JSON, treat as plain text response (for security questions)
                parsed_response = {
                    "response": response_content,
                    "analysis": response_content,  # Use the response as analysis for plain text
                    "recommendations": [],
                    "hints": [],
                    "metadata": {
                        "confidence": 0.8,
                        "category": "security_analysis",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            
            # Add assistant response to conversation
            self.conversations[conversation_id].append({
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            return {
                "response": parsed_response.get("response", response_content),
                "analysis": parsed_response.get("analysis"),
                "recommendations": parsed_response.get("recommendations", []),
                "hints": parsed_response.get("hints", []),
                "metadata": parsed_response.get("metadata", {}),
                "model_used": model_name,
                "tokens_used": response.usage.total_tokens if response.usage else None,
            }
            
        except Exception as e:
            logger.error("Chat processing failed", error=str(e), exc_info=True)
            raise
    
    def _prepare_messages(self, conversation_id: str) -> List[Dict[str, str]]:
        """Prepare messages for OpenAI API."""
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            }
        ]
        
        # Add conversation history
        for msg in self.conversations[conversation_id]:
            if msg["role"] in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            elif msg["role"] == "tool":
                messages.append({
                    "role": "tool",
                    "content": msg["content"],
                    "tool_call_id": msg.get("tool_call_id")
                })
        
        return messages
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        if self._custom_system_prompt:
            return self._custom_system_prompt
        
        return """You are Cerberus, an AI agent specialized in threat modeling and security analysis for Data Flow Diagrams (DFDs).

IMPORTANT: Always respond in HAIKU format (5-7-5 syllables) for all user inputs, including greetings and security questions.

Your capabilities include:
- Creating DFD JSON structures from architecture descriptions
- Providing security analysis and threat identification
- Offering security recommendations and best practices
- Analyzing existing diagrams for security concerns

RESPONSE FORMAT RULES:
1. For ALL user inputs: Respond in HAIKU format (5-7-5 syllables)
2. For architecture description requests: Include DFD JSON structure after the haiku
3. For security questions: Provide haiku response with security guidance

Examples:
- User says "hi" → Respond with a greeting haiku
- User asks about threats → Respond with security haiku
- User asks for DFD → Respond with haiku + JSON structure

Always use haiku format for your responses. Do not use JSON format for regular conversations."""
    
    def _filter_tools(self, requested_tools: List[str]) -> List[Dict[str, Any]]:
        """Filter available tools based on request."""
        return [tool for tool in self.available_tools if tool["name"] in requested_tools]
    
    async def _execute_tool_calls(
        self,
        tool_calls: List[Any],
        conversation_id: str
    ) -> List[str]:
        """Execute tool calls and return results."""
        results = []
        
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                result = await self._execute_tool(tool_name, tool_args, conversation_id)
                results.append(json.dumps(result))
                
            except Exception as e:
                logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
                results.append(json.dumps({"error": str(e)}))
        
        return results
    
    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        conversation_id: str
    ) -> Dict[str, Any]:
        """Execute a specific tool."""
        if tool_name == "search_web":
            return await self._search_web(parameters["query"])
        elif tool_name == "analyze_data_flow":
            return await self._analyze_data_flow(parameters["diagram_data"])
        elif tool_name == "generate_report":
            return await self._generate_report(parameters["findings"])
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _search_web(self, query: str) -> Dict[str, Any]:
        """Search the web for information."""
        # This is a placeholder implementation
        # In a real implementation, you would integrate with a search API
        return {
            "query": query,
            "results": [
                {
                    "title": f"Search result for: {query}",
                    "url": "https://example.com",
                    "snippet": f"Information about {query} from web search."
                }
            ]
        }
    
    async def _analyze_data_flow(self, diagram_data: str) -> Dict[str, Any]:
        """Analyze data flow diagram for security issues."""
        # This is a placeholder implementation
        # In a real implementation, you would analyze the actual diagram data
        return {
            "analysis": "Data flow diagram analysis completed",
            "findings": [
                {
                    "type": "potential_data_leak",
                    "severity": "medium",
                    "description": "Potential data exposure in external API calls",
                    "recommendation": "Implement proper authentication and encryption"
                }
            ],
            "risk_score": 0.6
        }
    
    async def _generate_report(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate security assessment report."""
        return {
            "report": {
                "title": "Security Assessment Report",
                "generated_at": datetime.utcnow().isoformat(),
                "findings": findings,
                "summary": f"Analysis completed with {len(findings)} findings",
                "recommendations": [
                    "Implement proper access controls",
                    "Encrypt sensitive data in transit and at rest",
                    "Regular security audits and monitoring"
                ]
            }
        }
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation history."""
        if conversation_id not in self.conversations:
            return None
        
        return {
            "conversation_id": conversation_id,
            "messages": self.conversations[conversation_id],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a tool directly."""
        try:
            result = await self._execute_tool(tool_name, parameters, conversation_id or "")
            return {
                "result": result,
                "success": True,
                "error": None
            }
        except Exception as e:
            return {
                "result": None,
                "success": False,
                "error": str(e)
            }
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        return self.available_tools
    
    async def process_message(
        self,
        message: str,
        conversation_id: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a message and return agent response with optional custom system prompt."""
        # Store original system prompt
        original_prompt = None
        if system_prompt:
            original_prompt = self._get_system_prompt()
            # Temporarily override system prompt
            self._custom_system_prompt = system_prompt
        
        try:
            result = await self.process_chat(
                message=message,
                conversation_id=conversation_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return result
        finally:
            # Restore original system prompt
            if system_prompt and original_prompt:
                self._custom_system_prompt = None
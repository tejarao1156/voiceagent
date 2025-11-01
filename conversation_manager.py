import json
import openai
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from config import OPENAI_API_KEY
import logging

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    TAKING_ORDER = "taking_order"
    CONFIRMING_ORDER = "confirming_order"
    COLLECTING_PAYMENT = "collecting_payment"
    COMPLETED = "completed"
    ERROR = "error"

class ConversationManager:
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the general voice agent"""
        return """You are a friendly and helpful voice agent. Your role is to:

1. Engage in natural, helpful conversations with users
2. Provide useful information and assistance
3. Be conversational and natural, not robotic
4. Ask clarifying questions when needed
5. Handle interruptions gracefully
6. Be patient and understanding
7. Always be polite and helpful
8. Keep responses concise but informative

Guidelines:
- Be conversational and natural, not robotic
- Ask one question at a time to avoid confusion
- Handle interruptions gracefully
- Be patient with users who may be unclear
- Always be polite and helpful
- If you don't understand something, ask for clarification
- Keep responses concise but informative

Current conversation state will be provided to help you understand context."""
    
    def create_session(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation session"""
        session_data = {
            "state": ConversationState.GREETING.value,
            "customer_id": customer_id,
            "order_items": [],
            "customer_info": {},
            "conversation_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Created new conversation session for customer: {customer_id}")
        return session_data
    
    def update_session_state(self, session_data: Dict[str, Any], new_state: ConversationState) -> Dict[str, Any]:
        """Update the conversation state"""
        session_data["state"] = new_state.value
        session_data["last_activity"] = datetime.utcnow().isoformat()
        return session_data
    
    def add_to_conversation_history(self, session_data: Dict[str, Any], user_input: str, agent_response: str) -> Dict[str, Any]:
        """Add interaction to conversation history"""
        interaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response
        }
        session_data["conversation_history"].append(interaction)
        session_data["last_activity"] = datetime.utcnow().isoformat()
        return session_data
    
    async def process_user_input(self, session_data: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """
        Process user input and generate appropriate response
        
        Args:
            session_data: Current conversation session data
            user_input: User's spoken/text input
            
        Returns:
            Updated session data and agent response
        """
        try:
            # Prepare context for the AI
            context = self._prepare_context(session_data)
            
            # Generate response using OpenAI
            response = await self._generate_response(context, user_input)
            
            # Update session based on response
            session_data = self._update_session_from_response(session_data, user_input, response)
            
            # Add to conversation history
            session_data = self.add_to_conversation_history(session_data, user_input, response["text"])
            
            return {
                "session_data": session_data,
                "response": response["text"],
                "next_state": response.get("next_state"),
                "actions": response.get("actions", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            session_data["state"] = ConversationState.ERROR.value
            return {
                "session_data": session_data,
                "response": "I'm sorry, I encountered an error. Could you please try again?",
                "next_state": ConversationState.ERROR.value,
                "actions": []
            }
    
    def _prepare_context(self, session_data: Dict[str, Any]) -> str:
        """Prepare context string for AI processing"""
        context = f"""
Current conversation state: {session_data['state']}
Customer ID: {session_data.get('customer_id', 'Unknown')}
Current conversation history: {len(session_data.get('conversation_history', []))} interactions
"""
        return context
    
    async def _generate_response(self, context: str, user_input: str) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt + "\n\nContext:\n" + context},
                {"role": "user", "content": user_input}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse response for state changes and actions
            parsed_response = self._parse_ai_response(response_text)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return {
                "text": "I'm sorry, I'm having trouble understanding. Could you please repeat that?",
                "next_state": None,
                "actions": []
            }
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response to extract state changes and actions"""
        # This is a simplified parser - in production, you might want more sophisticated parsing
        response = {
            "text": response_text,
            "next_state": None,
            "actions": []
        }
        
        # Simple keyword-based state detection
        response_lower = response_text.lower()
        
        if "what would you like to order" in response_lower or "menu" in response_lower:
            response["next_state"] = ConversationState.TAKING_ORDER.value
        elif "confirm" in response_lower and "order" in response_lower:
            response["next_state"] = ConversationState.CONFIRMING_ORDER.value
        elif "address" in response_lower or "phone" in response_lower:
            response["next_state"] = ConversationState.COLLECTING_INFO.value
        elif "thank you" in response_lower and "order" in response_lower:
            response["next_state"] = ConversationState.COMPLETED.value
        
        return response
    
    def _update_session_from_response(self, session_data: Dict[str, Any], user_input: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Update session data based on AI response"""
        if response.get("next_state"):
            session_data["state"] = response["next_state"]
        
        # Extract order items from user input (simplified)
        if session_data["state"] == ConversationState.TAKING_ORDER.value:
            # This would be more sophisticated in production
            # For now, we'll rely on the restaurant logic to handle this
            pass
        
        return session_data
    
    def get_session_summary(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of the current session"""
        return {
            "session_id": session_data.get("id"),
            "customer_id": session_data.get("customer_id"),
            "current_state": session_data["state"],
            "order_items_count": len(session_data.get("order_items", [])),
            "conversation_length": len(session_data.get("conversation_history", [])),
            "last_activity": session_data.get("last_activity"),
            "created_at": session_data.get("created_at")
        }

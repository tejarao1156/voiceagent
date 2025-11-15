"""
Twilio SMS Handler
Handles incoming SMS messages and generates AI responses using conversation manager
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TwilioSMSHandler:
    """Handle SMS messages and generate AI responses"""
    
    def __init__(self, conversation_tool):
        """Initialize SMS handler with conversation tool"""
        self.conversation_tool = conversation_tool
        # Track active conversations: {conversation_id: session_data}
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
    
    async def process_incoming_message(
        self,
        from_number: str,
        to_number: str,
        message_body: str,
        agent_config: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process incoming SMS message and generate AI response
        
        Args:
            from_number: Phone number that sent the message
            to_number: Phone number that received the message (agent number)
            message_body: Text content of the message
            agent_config: Agent configuration (system prompt, greeting, etc.)
            conversation_history: Previous messages in this conversation for personalization
        
        Returns:
            Dictionary with:
                - response_text: AI-generated response
                - session_data: Updated session data
                - is_greeting: Whether this is the first message (should send greeting)
        """
        try:
            # Create conversation ID from phone numbers (sorted for consistency)
            phone_numbers = sorted([from_number, to_number])
            conversation_id = f"conv_{phone_numbers[0]}_{phone_numbers[1]}"
            
            # Get or create session data for this conversation
            if conversation_id not in self.active_conversations:
                # Create new session
                session_data = self.conversation_tool.conversation_manager.create_session(
                    customer_id=from_number
                )
                # Override system prompt with agent's system prompt
                if agent_config.get("systemPrompt"):
                    session_data["system_prompt"] = agent_config.get("systemPrompt")
                self.active_conversations[conversation_id] = session_data
                is_first_message = True
            else:
                session_data = self.active_conversations[conversation_id]
                is_first_message = False
            
            # If this is the first message, send greeting
            if is_first_message:
                greeting = agent_config.get("greeting", "Hello! How can I help you today?")
                logger.info(f"📱 First message from {from_number}, sending greeting: {greeting[:50]}...")
                
                # Update session with greeting
                session_data = self.conversation_tool.conversation_manager.add_to_conversation_history(
                    session_data,
                    user_input=message_body,
                    agent_response=greeting
                )
                self.active_conversations[conversation_id] = session_data
                
                return {
                    "response_text": greeting,
                    "session_data": session_data,
                    "is_greeting": True
                }
            
            # Build conversation history from previous messages for context
            if conversation_history:
                # Convert message history to conversation history format
                for msg in conversation_history:
                    if msg.get("role") == "user":
                        # This is a user message - add to conversation history
                        user_text = msg.get("body", "")
                        # Find corresponding assistant response if available
                        assistant_response = None
                        for next_msg in conversation_history[conversation_history.index(msg) + 1:]:
                            if next_msg.get("role") == "assistant":
                                assistant_response = next_msg.get("body", "")
                                break
                        
                        if user_text:
                            if assistant_response:
                                # Add both user input and assistant response
                                session_data = self.conversation_tool.conversation_manager.add_to_conversation_history(
                                    session_data,
                                    user_input=user_text,
                                    agent_response=assistant_response
                                )
                            else:
                                # Only user input (no response yet)
                                session_data["conversation_history"].append({
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "user_input": user_text,
                                    "agent_response": ""
                                })
            
            # Get agent configuration and override system prompt
            system_prompt = agent_config.get("systemPrompt", "")
            if system_prompt:
                # Store system prompt in session data for conversation manager to use
                session_data["system_prompt"] = system_prompt
            
            llm_model = agent_config.get("inferenceModel", "gpt-4o-mini")
            temperature = agent_config.get("temperature", 0.7)
            max_tokens = agent_config.get("maxTokens", 500)
            
            # Generate AI response using conversation tool
            logger.info(f"🤖 Generating AI response for message from {from_number}")
            ai_response = await self.conversation_tool.generate_response(
                session_data,
                message_body,
                None,  # No persona config for SMS
                model=llm_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response text
            response_text = ai_response.get("response", "")
            updated_session_data = ai_response.get("session_data", session_data)
            
            # Update active conversation
            self.active_conversations[conversation_id] = updated_session_data
            
            logger.info(f"✅ Generated response: {response_text[:50]}...")
            
            return {
                "response_text": response_text,
                "session_data": updated_session_data,
                "is_greeting": False
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing incoming message: {e}", exc_info=True)
            # Return a fallback response
            return {
                "response_text": "I apologize, but I encountered an error processing your message. Please try again.",
                "session_data": session_data if 'session_data' in locals() else {},
                "is_greeting": False
            }


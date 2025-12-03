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
            # Determine if this is a new conversation based on MongoDB history
            # If conversation_history is empty or None, it's a new conversation
            is_new_conversation = not conversation_history or len(conversation_history) == 0
            
            logger.info(f"📝 Conversation status: {'NEW' if is_new_conversation else 'EXISTING'}")
            if conversation_history:
                logger.info(f"📝 Found {len(conversation_history)} previous message(s) in conversation history")
            
            # Create new session data using ConversationalResponseTool's create_session method
            session_data = self.conversation_tool.create_session(
                customer_id=from_number
            )
            
            # Override system prompt with agent's system prompt
            if agent_config.get("systemPrompt"):
                session_data["system_prompt"] = agent_config.get("systemPrompt")
            
            # If this is a NEW conversation, send greeting
            if is_new_conversation:
                greeting = agent_config.get("greeting", "Hello! How can I help you today?")
                logger.info(f"📱 NEW conversation with {from_number}, sending greeting: {greeting[:50]}...")
                
                # Update session with greeting
                session_data = self.conversation_tool.manager.add_to_conversation_history(
                    session_data,
                    user_input=message_body,
                    agent_response=greeting
                )
                
                return {
                    "response_text": greeting,
                    "session_data": session_data,
                    "is_greeting": True
                }
            
            # EXISTING conversation - build conversation history from MongoDB messages
            logger.info(f"📚 Building conversation history from {len(conversation_history)} previous message(s)")
            
            # Convert MongoDB message history to conversation history format
            # Messages are already sorted by timestamp in get_all_messages_by_agent_id
            # Format: [{"role": "user", "body": "...", "timestamp": "..."}, {"role": "assistant", "body": "...", "timestamp": "..."}]
            # Process messages in chronological order, pairing user and assistant messages
            user_message = None
            user_timestamp = None
            for msg in conversation_history:
                role = msg.get("role")  # "user" or "assistant" (from role field or derived from direction)
                text = msg.get("body", "")  # Message body from MongoDB
                timestamp = msg.get("timestamp", datetime.utcnow().isoformat())
                
                if not text:
                    continue
                
                if role == "user":
                    # If we have a previous user message without response, add it with empty response
                    if user_message:
                        logger.debug(f"📝 Adding user message without response to history")
                        session_data = self.conversation_tool.manager.add_to_conversation_history(
                            session_data,
                            user_input=user_message,
                            agent_response=""
                        )
                    # Store current user message
                    user_message = text
                    user_timestamp = timestamp
                elif role == "assistant":
                    if user_message:
                        # Found assistant response for previous user message
                        # Add both user input and assistant response as a pair
                        session_data = self.conversation_tool.manager.add_to_conversation_history(
                            session_data,
                            user_input=user_message,
                            agent_response=text
                        )
                        user_message = None  # Reset for next pair
                        user_timestamp = None
                    else:
                        # Assistant message without preceding user message (edge case)
                        # This shouldn't happen in normal flow, but handle gracefully
                        logger.warning(f"⚠️ Found assistant message without preceding user message")
            
            # If there's a user message without a response at the end, add it
            if user_message:
                logger.info(f"📝 Adding final user message without response to history")
                session_data["conversation_history"].append({
                    "timestamp": user_timestamp or datetime.utcnow().isoformat(),
                    "user_input": user_message,
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


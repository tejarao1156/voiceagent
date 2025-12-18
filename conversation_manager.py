import json
import openai
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from config import OPENAI_API_KEY, INFERENCE_MODEL
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

CRITICAL: Always respond to the MOST RECENT user query. The conversation history is provided for context, but you must prioritize and directly address the user's current/latest question or statement. Do not respond to questions from earlier in the conversation unless the user explicitly references them.

Guidelines:
- Be conversational and natural, not robotic
- Ask one question at a time to avoid confusion
- Handle interruptions gracefully - when interrupted, respond to the NEW question, not the previous one
- Be patient with users who may be unclear
- Always be polite and helpful
- If you don't understand something, ask for clarification
- Keep responses concise but informative
- ALWAYS respond to the most recent user input - ignore older queries unless explicitly referenced

Current conversation state will be provided to help you understand context.

CRITICAL INSTRUCTIONS:
- Always respond to the MOST RECENT user query.
- If the user says something unclear or if you hear silence/noise, DO NOT say "Bye". Instead, ask "I'm sorry, I didn't catch that. Could you please repeat?" or "Are you still there?"
- Only say "Bye" or end the conversation if the user explicitly says "Bye", "Goodbye", or indicates they want to end the call.
- Never assume the conversation is over based on a short input.

CONVERSATION CLOSURE BEHAVIOR:
- After helping the user with their request, always ask: "Is there anything else I can help you with today?"
- If the user says "no", "no thanks", "that's all", "I'm good", or similar, respond with: "Thank you for calling! Have a great day. Goodbye!"
- When you say "Goodbye" at the end, the system will automatically end the call.
- Be proactive in checking if the user needs more help after each completed request."""
    
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
    
    async def process_user_input(
        self,
        session_data: Dict[str, Any],
        user_input: str,
        persona_config: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
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
            context = self._prepare_context(session_data, persona_config)
            
            # Get conversation history (ensure it exists and is a list)
            conversation_history = session_data.get("conversation_history", [])
            if not isinstance(conversation_history, list):
                conversation_history = []
                session_data["conversation_history"] = conversation_history
            
            # Get custom system prompt from session_data if available (for messaging agents)
            custom_system_prompt = session_data.get("system_prompt")
            
            # Generate response using OpenAI with conversation history
            response = await self._generate_response(
                context, user_input, conversation_history, persona_config,
                model=model, temperature=temperature, max_tokens=max_tokens,
                custom_system_prompt=custom_system_prompt
            )
            
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
    
    def _prepare_context(
        self,
        session_data: Dict[str, Any],
        persona_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare context string for AI processing"""
        context = f"""
Current conversation state: {session_data.get('state', 'greeting')}
Customer ID: {session_data.get('customer_id', 'Unknown')}
Current conversation history: {len(session_data.get('conversation_history', []))} interactions
"""
        if persona_config:
            context += (
                f"Persona: {persona_config.get('display_name', persona_config.get('id'))}\n"
                f"Persona description: {persona_config.get('description', 'N/A')}\n"
            )
        return context
    
    async def _generate_response(
        self,
        context: str,
        user_input: str,
        conversation_history: List[Dict[str, Any]],
        persona_config: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        custom_system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate response using OpenAI with conversation history"""
        try:
            # Use custom system prompt if provided (from agent config for messaging)
            if custom_system_prompt:
                system_prompt = custom_system_prompt
            elif persona_config and persona_config.get("conversation_prompt"):
                system_prompt = (
                    self.system_prompt
                    + "\n\nPersona Style Instructions:\n"
                    + persona_config["conversation_prompt"]
                )
            else:
                system_prompt = self.system_prompt

            # Build messages array with conversation history
            messages = [
                {"role": "system", "content": system_prompt + "\n\nContext:\n" + context}
            ]
            
            # CRITICAL: Prioritize last 4 messages for context while summarizing older ones
            # This prevents token overflow while maintaining relevant context
            logger.info(f"📚 Building messages array with {len(conversation_history)} previous interactions")
            
            # If more than 4 interactions, summarize older ones and include last 4 in full
            if len(conversation_history) > 4:
                # Summarize older interactions (before last 4)
                older_interactions = conversation_history[:-4]
                summary_parts = []
                for interaction in older_interactions:
                    user_input_summary = interaction.get("user_input", "")[:100]
                    agent_response_summary = interaction.get("agent_response", "")[:100]
                    summary_parts.append(f"User: {user_input_summary}... AI: {agent_response_summary}...")
                
                summary_text = "[Earlier conversation summary: " + " | ".join(summary_parts) + "]"
                messages.append({"role": "system", "content": summary_text})
                logger.info(f"   Added summary of {len(older_interactions)} older interactions")
                
                # Add last 4 interactions in full
                recent_interactions = conversation_history[-4:]
            else:
                recent_interactions = conversation_history
            
            # Add recent interactions in full detail (last 4 or all if fewer)
            for idx, interaction in enumerate(recent_interactions):
                # Add user message
                if interaction.get("user_input"):
                    messages.append({
                        "role": "user",
                        "content": interaction["user_input"]
                    })
                    logger.debug(f"   Added recent[{idx}] user: '{interaction['user_input'][:50]}...'")
                # Add assistant response
                if interaction.get("agent_response"):
                    messages.append({
                        "role": "assistant",
                        "content": interaction["agent_response"]
                    })
                    logger.debug(f"   Added recent[{idx}] assistant: '{interaction['agent_response'][:50]}...'")
            
            # Add current user input (this is the question we're answering now)
            messages.append({"role": "user", "content": user_input})
            logger.info(f"📝 Added current user input: '{user_input[:50]}...'")
            logger.info(f"📊 Total messages being sent to AI: {len(messages)} (1 system + {len(conversation_history) * 2} history + 1 current)")
            
            # Use provided model/temperature/maxTokens or fall back to defaults
            inference_model = model or INFERENCE_MODEL
            temp = temperature if temperature is not None else 0.7
            max_toks = max_tokens if max_tokens is not None else 800
            
            # Use streaming for faster response (get chunks as they arrive)
            stream = self.client.chat.completions.create(
                model=inference_model,
                messages=messages,
                temperature=temp,
                max_tokens=max_toks,
                stream=True  # Enable streaming for faster first token
            )
            
            # Collect streaming response chunks
            response_text = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    response_text += chunk.choices[0].delta.content
            
            response_text = response_text.strip()
            
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
    
    def _split_into_complete_sentences(self, text: str) -> List[str]:
        """Split text into sentences, keeping incomplete fragments.
        
        Returns:
            List of sentences. Last item may be incomplete fragment.
        """
        import re
        # Split on sentence endings followed by space or end of string
        # Keep the punctuation with the sentence
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s for s in sentences if s.strip()]
    
    async def _generate_response_streaming(
        self,
        context: str,
        user_input: str,
        conversation_history: List[Dict[str, Any]],
        persona_config: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        custom_system_prompt: Optional[str] = None
    ):
        """Generate response using OpenAI streaming, yielding complete sentences.
        
        This is an async generator that yields sentences as they're generated,
        enabling real-time TTS while LLM is still generating the full response.
        
        Yields:
            str: Complete sentences as they become available
        """
        try:
            # Use custom system prompt if provided
            if custom_system_prompt:
                system_prompt = custom_system_prompt
            elif persona_config and persona_config.get("conversation_prompt"):
                system_prompt = (
                    self.system_prompt
                    + "\n\nPersona Style Instructions:\n"
                    + persona_config["conversation_prompt"]
                )
            else:
                system_prompt = self.system_prompt

            # Build messages array with conversation history
            messages = [
                {"role": "system", "content": system_prompt + "\n\nContext:\n" + context}
            ]
            
            # Add conversation history (limit to last 4 to keep context tight)
            if len(conversation_history) > 4:
                recent_interactions = conversation_history[-4:]
            else:
                recent_interactions = conversation_history
            
            for interaction in recent_interactions:
                if interaction.get("user_input"):
                    messages.append({"role": "user", "content": interaction["user_input"]})
                if interaction.get("agent_response"):
                    messages.append({"role": "assistant", "content": interaction["agent_response"]})
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Use provided model/temperature/maxTokens or fall back to defaults
            inference_model = model or INFERENCE_MODEL
            temp = temperature if temperature is not None else 0.7
            max_toks = max_tokens if max_tokens is not None else 200  # Reduced default
            
            logger.info(f"🚀 Starting streaming LLM response (model={inference_model}, max_tokens={max_toks})")
            
            # Create streaming response
            stream = self.client.chat.completions.create(
                model=inference_model,
                messages=messages,
                temperature=temp,
                max_tokens=max_toks,
                stream=True
            )
            
            # Buffer to accumulate text until we have a complete sentence
            buffer = ""
            sentence_count = 0
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    buffer += chunk.choices[0].delta.content
                    
                    # Check for sentence boundaries (. ! ?)
                    # Yield complete sentences as they become available
                    while True:
                        # Find the first sentence boundary
                        match = None
                        for i, char in enumerate(buffer):
                            if char in '.!?' and i < len(buffer) - 1 and buffer[i + 1] in ' \n':
                                match = i + 1
                                break
                        
                        if match:
                            sentence = buffer[:match].strip()
                            buffer = buffer[match:].strip()
                            if sentence:
                                sentence_count += 1
                                logger.info(f"📝 Yielding sentence #{sentence_count}: '{sentence[:50]}...'")
                                yield sentence
                        else:
                            break
            
            # Yield any remaining text in buffer (incomplete sentence at end)
            if buffer.strip():
                sentence_count += 1
                logger.info(f"📝 Yielding final fragment #{sentence_count}: '{buffer.strip()[:50]}...'")
                yield buffer.strip()
            
            logger.info(f"✅ Streaming complete: {sentence_count} sentences yielded")
            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield "I'm sorry, I'm having trouble understanding. Could you please repeat that?"

    
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

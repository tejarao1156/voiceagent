"""
MongoDB Models for Conversation Storage
Defines the structure for storing conversations in MongoDB
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId

class ConversationMessage(BaseModel):
    """Individual message in a conversation"""
    timestamp: str = Field(..., description="ISO timestamp of the message")
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class ConversationSession(BaseModel):
    """Conversation session model for MongoDB"""
    session_id: str = Field(..., description="Unique session identifier")
    customer_id: Optional[str] = Field(None, description="Customer ID")
    agent_id: Optional[str] = Field(None, description="Agent/phone number ID")
    persona: Optional[str] = Field(None, description="Persona identifier")
    status: str = Field(default="active", description="Session status: active, completed, abandoned")
    state: Optional[str] = Field(None, description="Current conversation state")
    messages: List[ConversationMessage] = Field(default_factory=list, description="Conversation messages")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional session metadata")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Creation timestamp")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Last update timestamp")
    
    class Config:
        json_encoders = {
            ObjectId: str
        }

def conversation_to_dict(conversation: ConversationSession) -> Dict[str, Any]:
    """Convert ConversationSession to MongoDB document"""
    return {
        "session_id": conversation.session_id,
        "customer_id": conversation.customer_id,
        "agent_id": conversation.agent_id,
        "persona": conversation.persona,
        "status": conversation.status,
        "state": conversation.state,
        "messages": [msg.dict() for msg in conversation.messages],
        "metadata": conversation.metadata,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }

def dict_to_conversation(doc: Dict[str, Any]) -> ConversationSession:
    """Convert MongoDB document to ConversationSession"""
    return ConversationSession(
        session_id=doc.get("session_id"),
        customer_id=doc.get("customer_id"),
        agent_id=doc.get("agent_id"),
        persona=doc.get("persona"),
        status=doc.get("status", "active"),
        state=doc.get("state"),
        messages=[ConversationMessage(**msg) for msg in doc.get("messages", [])],
        metadata=doc.get("metadata", {}),
        created_at=doc.get("created_at", datetime.utcnow().isoformat()),
        updated_at=doc.get("updated_at", datetime.utcnow().isoformat()),
    )


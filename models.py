"""
Unified Models for Voice Agent System
This module contains both SQLAlchemy database models and Pydantic API schemas.
"""

# ============================================================================
# IMPORTS
# ============================================================================

# SQLAlchemy imports for database models
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

# Pydantic imports for API schemas
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# ============================================================================
# DATABASE MODELS (SQLAlchemy ORM)
# ============================================================================

Base = declarative_base()

class Customer(Base):
    """Customer database model"""
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String, unique=True, nullable=False)
    name = Column(String)
    email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # orders = relationship("Order", back_populates="customer")  # Commented out - Order model not defined

class ConversationSession(Base):
    """Conversation session database model"""
    __tablename__ = "conversation_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customers.id"))
    session_data = Column(Text)  # JSON string storing conversation state
    status = Column(String, default="active")  # active, completed, abandoned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer")

# ============================================================================
# API SCHEMAS (Pydantic Models)
# ============================================================================

# General API Models
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Health status", example="healthy")
    timestamp: str = Field(..., description="Current timestamp", example="2024-01-01T00:00:00Z")
    version: str = Field(..., description="API version", example="1.0.0")

class RootResponse(BaseModel):
    """Root endpoint response model"""
    message: str = Field(..., description="API message", example="Voice Agent API")
    version: str = Field(..., description="API version", example="1.0.0")
    status: str = Field(..., description="API status", example="running")
    documentation: str = Field(..., description="Documentation URL", example="/docs")
    health_check: str = Field(..., description="Health check URL", example="/health")

# Voice Processing Models
class VoiceInputRequest(BaseModel):
    """Voice input request model"""
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    customer_id: Optional[str] = Field(None, description="Customer ID")

class VoiceInputResponse(BaseModel):
    """Voice input response model"""
    success: bool = Field(..., description="Whether the operation was successful")
    text: Optional[str] = Field(None, description="Transcribed text from audio")
    error: Optional[str] = Field(None, description="Error message if operation failed")

class VoiceOutputRequest(BaseModel):
    """Voice output request model"""
    text: str = Field(..., description="Text to convert to speech", example="Hello, how can I help you?")
    voice: Optional[str] = Field("alloy", description="Voice to use", example="alloy")

class VoiceOutputResponse(BaseModel):
    """Voice output response model"""
    success: bool = Field(..., description="Whether the operation was successful")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio data")
    text: Optional[str] = Field(None, description="Original text")
    error: Optional[str] = Field(None, description="Error message if operation failed")

# Conversation Models
class ConversationRequest(BaseModel):
    """Conversation request model"""
    text: str = Field(..., description="User input text", example="Hello, how can you help me?")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    customer_id: Optional[str] = Field(None, description="Customer ID")

class ConversationResponse(BaseModel):
    """Conversation response model"""
    response: str = Field(..., description="Agent response text")
    session_data: Dict[str, Any] = Field(..., description="Updated session data")
    next_state: Optional[str] = Field(None, description="Next conversation state")
    actions: List[str] = Field(default=[], description="Actions to take")

class ConversationStartRequest(BaseModel):
    """Conversation start request model"""
    customer_id: Optional[str] = Field(None, description="Customer ID")

class ConversationStartResponse(BaseModel):
    """Conversation start response model"""
    session_id: str = Field(..., description="New session ID")
    session_data: Dict[str, Any] = Field(..., description="Initial session data")
    message: str = Field(..., description="Success message")

# Voice Agent Pipeline Models
class VoiceAgentProcessResponse(BaseModel):
    """Voice agent process response model"""
    success: bool = Field(..., description="Whether the operation was successful")
    user_input: Optional[str] = Field(None, description="Transcribed user input")
    agent_response: Optional[str] = Field(None, description="Agent response text")
    audio_response: Optional[str] = Field(None, description="Base64 encoded audio response")
    session_data: Optional[Dict[str, Any]] = Field(None, description="Updated session data")
    next_state: Optional[str] = Field(None, description="Next conversation state")
    actions: List[str] = Field(default=[], description="Actions to take")

# Error Models
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(..., description="Error timestamp")

# Utility Models
class SuccessResponse(BaseModel):
    """Generic success response model"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    timestamp: Optional[str] = Field(None, description="Response timestamp")

class PaginationRequest(BaseModel):
    """Pagination request model"""
    page: int = Field(1, description="Page number", ge=1)
    limit: int = Field(10, description="Items per page", ge=1, le=100)

class PaginationResponse(BaseModel):
    """Pagination response model"""
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total items")
    pages: int = Field(..., description="Total pages")

# ============================================================================
# EXPORTS
# ============================================================================

# Database models
__all__ = [
    # Database models
    "Base", "Customer", "ConversationSession",
    
    # API schemas
    "HealthResponse", "RootResponse",
    "VoiceInputRequest", "VoiceInputResponse", 
    "VoiceOutputRequest", "VoiceOutputResponse",
    "ConversationRequest", "ConversationResponse",
    "ConversationStartRequest", "ConversationStartResponse",
    "VoiceAgentProcessResponse",
    "ErrorResponse", "SuccessResponse",
    "PaginationRequest", "PaginationResponse"
]

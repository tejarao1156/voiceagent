"""
Pydantic models for MongoDB phone number configurations.
These models define the structure for storing phone-specific AI configurations.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PhoneNumberConfig(BaseModel):
    """Configuration for a specific Twilio phone number"""

    # Required Fields
    phone_number: str = Field(..., description="Twilio phone number (e.g., +1234567890)", example="+18668134984")
    display_name: str = Field(..., description="Human-readable name for this number", example="Customer Service Line")

    # Voice Processing Configuration
    stt_model: str = Field(default="whisper-1", description="Speech-to-text model ID", example="whisper-1")
    tts_model: str = Field(default="tts-1", description="Text-to-speech model (tts-1 or tts-1-hd)", example="tts-1")
    tts_voice: str = Field(default="alloy", description="TTS voice (alloy, echo, fable, onyx, nova, shimmer)", example="nova")

    # LLM Configuration
    inference_model: str = Field(default="gpt-4o-mini", description="OpenAI GPT model", example="gpt-4o-mini")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature (0.0-2.0)", example=0.7)
    max_tokens: int = Field(default=500, ge=1, le=4000, description="Maximum tokens for LLM response", example=500)

    # Behavior Configuration
    system_prompt: str = Field(..., description="Custom system prompt for AI behavior", example="You are a helpful customer support agent...")
    greeting: str = Field(..., description="Custom greeting message when call starts", example="Welcome to customer support!")

    # Advanced Features
    enable_interrupts: bool = Field(default=True, description="Allow user to interrupt AI responses")
    interrupt_timeout: float = Field(default=0.5, ge=0.1, le=5.0, description="Timeout for interrupt detection (seconds)")

    # Recording Configuration
    enable_recording: bool = Field(default=True, description="Enable call recording")
    max_call_duration: int = Field(default=3600, ge=60, description="Maximum call duration in seconds", example=3600)

    # Status
    is_active: bool = Field(default=True, description="Whether this configuration is active")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "+18668134984",
                "display_name": "Main Support Line",
                "stt_model": "whisper-1",
                "tts_model": "tts-1",
                "tts_voice": "nova",
                "inference_model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 500,
                "system_prompt": "You are a helpful customer support agent. Provide concise, friendly responses.",
                "greeting": "Welcome to customer support! How can I help you today?",
                "enable_interrupts": True,
                "interrupt_timeout": 0.5,
                "enable_recording": True,
                "max_call_duration": 3600,
                "is_active": True
            }
        }


class PhoneNumberConfigUpdate(BaseModel):
    """Model for partial updates to phone number configuration"""
    
    display_name: Optional[str] = None
    stt_model: Optional[str] = None
    tts_model: Optional[str] = None
    tts_voice: Optional[str] = None
    inference_model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4000)
    system_prompt: Optional[str] = None
    greeting: Optional[str] = None
    enable_interrupts: Optional[bool] = None
    interrupt_timeout: Optional[float] = Field(default=None, ge=0.1, le=5.0)
    enable_recording: Optional[bool] = None
    max_call_duration: Optional[int] = Field(default=None, ge=60)
    is_active: Optional[bool] = None

"""
Voice Agent Main Application
This is the main entry point for the voice agent system.
It imports and runs the API from api_general.py
"""

import uvicorn
import logging
from api_general import app
from config import API_HOST, API_PORT, DEBUG, RELOAD

# Custom filter to suppress noisy polling logs
class PollingLogFilter(logging.Filter):
    """Filter out repetitive polling endpoint logs to reduce noise."""
    SUPPRESSED_PATHS = ["/api/calls", "/health", "/analytics/"]
    
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        # Suppress GET requests to polling endpoints
        for path in self.SUPPRESSED_PATHS:
            if f'GET {path}' in message and '200' in message:
                return False
        return True

if __name__ == "__main__":
    # Add filter to uvicorn access logger
    logging.getLogger("uvicorn.access").addFilter(PollingLogFilter())
    
    uvicorn.run(
        "api_general:app", 
        host=API_HOST, 
        port=API_PORT,
        reload=RELOAD and DEBUG
    )

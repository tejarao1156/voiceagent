"""
Voice Agent Main Application
This is the main entry point for the voice agent system.
It imports and runs the API from api_general.py
"""

import uvicorn
from api_general import app
from config import API_HOST, API_PORT, DEBUG, RELOAD

if __name__ == "__main__":
    uvicorn.run(
        "api_general:app", 
        host=API_HOST, 
        port=API_PORT,
        reload=RELOAD and DEBUG
    )

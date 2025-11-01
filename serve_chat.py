#!/usr/bin/env python3
"""
Simple HTTP server to serve the chat UI
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def serve_chat_ui():
    """Serve the chat UI on localhost"""
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    chat_ui_path = script_dir / "chat_ui.html"
    
    if not chat_ui_path.exists():
        print("❌ Error: chat_ui.html not found!")
        return
    
    # Change to the script directory
    os.chdir(script_dir)
    
    PORT = 3000
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=script_dir, **kwargs)
        
        def end_headers(self):
            # Add CORS headers
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print("🚀 Chat UI Server Starting...")
            print(f"📱 Chat UI: http://localhost:{PORT}/chat_ui.html")
            print(f"🔧 API Server: http://localhost:8000")
            print("=" * 50)
            print("✅ Both servers are running!")
            print("🌐 Opening chat UI in your browser...")
            print("⏹️  Press Ctrl+C to stop")
            
            # Open browser
            webbrowser.open(f"http://localhost:{PORT}/chat_ui.html")
            
            # Start server
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Chat UI server stopped")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use")
            print("💡 Try closing other applications or use a different port")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    serve_chat_ui()

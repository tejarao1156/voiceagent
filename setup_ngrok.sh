#!/bin/bash

echo "🔧 ngrok Setup Script"
echo ""
echo "This script will help you set up ngrok for Twilio webhooks."
echo ""

# Check for local ngrok binary first
NGROK_CMD=""
if [ -f "./bin/ngrok" ]; then
    NGROK_CMD="./bin/ngrok"
    echo "✅ Found local ngrok binary: ./bin/ngrok"
elif command -v ngrok &> /dev/null; then
    NGROK_CMD="ngrok"
    echo "✅ Found ngrok in PATH"
else
    echo "❌ ngrok is not installed."
    echo ""
    echo "📥 Installing ngrok locally..."
    echo ""
    
    # Create bin directory if it doesn't exist
    mkdir -p ./bin
    
    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip"
    elif [ "$ARCH" = "x86_64" ]; then
        NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip"
    else
        echo "❌ Unsupported architecture: $ARCH"
        echo "   Please download ngrok manually from: https://ngrok.com/download"
        exit 1
    fi
    
    echo "   Downloading ngrok for $ARCH..."
    curl -o /tmp/ngrok.zip "$NGROK_URL" 2>&1 | grep -E "(Total|Error)" || true
    
    if [ -f /tmp/ngrok.zip ]; then
        echo "   Extracting ngrok..."
        unzip -o /tmp/ngrok.zip -d /tmp/ 2>&1 | grep -E "(inflating|Error)" || true
        if [ -f /tmp/ngrok ]; then
            cp /tmp/ngrok ./bin/ngrok
            chmod +x ./bin/ngrok
            NGROK_CMD="./bin/ngrok"
            echo "✅ ngrok installed successfully in ./bin/ngrok"
            rm -f /tmp/ngrok.zip /tmp/ngrok
        else
            echo "❌ Failed to extract ngrok"
            exit 1
        fi
    else
        echo "❌ Failed to download ngrok"
        exit 1
    fi
fi

echo "✅ ngrok is installed"
echo ""

# Check if authtoken is already configured
if $NGROK_CMD config check &> /dev/null 2>&1; then
    echo "✅ ngrok authtoken is already configured!"
    echo ""
    read -p "Do you want to start ngrok now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🚀 Starting ngrok..."
        echo ""
        echo "📋 Steps:"
        echo "1. ngrok will start and show a URL like: https://abc123.ngrok.io"
        echo "2. Copy that URL"
        echo "3. Update your .env file: TWILIO_WEBHOOK_BASE_URL=https://abc123.ngrok.io"
        echo "4. Update Twilio Console webhook URL"
        echo ""
        echo "Starting ngrok on port 4002..."
        echo "Press Ctrl+C to stop ngrok"
        echo ""
        $NGROK_CMD http 4002
    fi
else
    echo "⚠️  ngrok authtoken is not configured."
    echo ""
    echo "📝 To set up ngrok:"
    echo ""
    echo "1. Sign up for a FREE ngrok account:"
    echo "   👉 https://dashboard.ngrok.com/signup"
    echo ""
    echo "2. Get your authtoken:"
    echo "   👉 https://dashboard.ngrok.com/get-started/your-authtoken"
    echo ""
    echo "3. Copy your authtoken and run:"
    echo "   ngrok config add-authtoken YOUR_TOKEN_HERE"
    echo ""
    echo "4. Then run this script again to start ngrok"
    echo ""
    read -p "Do you have your authtoken ready? Enter it now (or press Enter to skip): " AUTHTOKEN
    if [ -n "$AUTHTOKEN" ]; then
        # Verify ngrok is still available before trying to configure
        if [ -z "$NGROK_CMD" ]; then
            echo "❌ ngrok command not found. Please install ngrok first."
            echo "   See installation instructions above."
            exit 1
        fi
        
        $NGROK_CMD config add-authtoken "$AUTHTOKEN" 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ Authtoken configured successfully!"
            echo ""
            echo "🚀 Starting ngrok..."
            echo ""
            $NGROK_CMD http 4002
        else
            echo "❌ Failed to configure authtoken. Please check your token and try again."
            echo "   You can also configure it manually by running:"
            echo "   ngrok config add-authtoken YOUR_TOKEN_HERE"
        fi
    else
        echo "ℹ️  You can set up ngrok later. Run this script again when ready."
    fi
fi


#!/bin/bash

echo "🔧 ngrok Setup Script"
echo ""
echo "This script will help you set up ngrok for Twilio webhooks."
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed."
    echo "Installing ngrok..."
    brew install ngrok
fi

echo "✅ ngrok is installed"
echo ""

# Check if authtoken is already configured
if ngrok config check &> /dev/null; then
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
        ngrok http 4002
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
        ngrok config add-authtoken "$AUTHTOKEN"
        if [ $? -eq 0 ]; then
            echo "✅ Authtoken configured successfully!"
            echo ""
            echo "🚀 Starting ngrok..."
            echo ""
            ngrok http 4002
        else
            echo "❌ Failed to configure authtoken. Please check your token and try again."
        fi
    else
        echo "ℹ️  You can set up ngrok later. Run this script again when ready."
    fi
fi


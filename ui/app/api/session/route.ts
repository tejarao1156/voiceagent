import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const apiKey = process.env.OPENAI_API_KEY;
    
    if (!apiKey) {
      return NextResponse.json(
        { error: 'OPENAI_API_KEY not found in environment variables' },
        { status: 500 }
      );
    }

    // Create a new Realtime API session
    const response = await fetch('https://api.openai.com/v1/realtime/sessions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-realtime-preview-2024-12-17',
        voice: 'verse',
        input_audio_format: 'pcm16',
        output_audio_format: 'pcm16',
        turn_detection: {
          type: 'server_vad',
        },
        instructions: 'You are a friendly restaurant AI assistant who chats naturally, answers menu questions, and helps customers order food.',
      }),
    });

    if (!response.ok) {
      const errorData = await response.text();
      console.error('OpenAI API error:', errorData);
      return NextResponse.json(
        { error: `Failed to create session: ${errorData}` },
        { status: response.status }
      );
    }

    const sessionData = await response.json();
    
    return NextResponse.json({
      session: sessionData,
      ws_url: `wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17`,
    });
    
  } catch (error: any) {
    console.error('Error creating session:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}


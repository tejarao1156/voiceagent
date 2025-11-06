import { NextRequest, NextResponse } from 'next/server';

type PersonaPreset = {
  id: string;
  voice: string;
  realtimeModel: string;
  instructions: string;
};

const PERSONA_PRESETS: Record<string, PersonaPreset> = {
  friendly_guide: {
    id: 'friendly_guide',
    voice: 'verse',
    realtimeModel: 'gpt-4o-realtime-preview-2024-12-17',
    instructions:
      'You are a friendly and encouraging guide. Keep responses upbeat, supportive, and conversational. Offer gentle suggestions and highlight positive takeaways.',
  },
  calm_concierge: {
    id: 'calm_concierge',
    voice: 'sol',
    realtimeModel: 'gpt-4o-realtime-preview-2024-12-17',
    instructions:
      'Respond like a seasoned hotel concierge: calm, articulate, and confident. Offer concise explanations and reassure the customer with professional poise.',
  },
  energetic_host: {
    id: 'energetic_host',
    voice: 'alloy',
    realtimeModel: 'gpt-4o-realtime-preview-2024-12-17',
    instructions:
      'Channel an energetic event host. Keep a lively pace, express excitement, and motivate the user to stay engaged with enthusiastic language.',
  },
  american_frontdesk: {
    id: 'american_frontdesk',
    voice: 'amber',
    realtimeModel: 'gpt-4o-realtime-preview-2024-12-17',
    instructions:
      'Sound like a welcoming American restaurant host. Be warm, attentive, and service-oriented. Use phrases like "absolutely" and "let me take care of that for you" while keeping a confident, relaxed pace.',
  },
  fine_dining_host: {
    id: 'fine_dining_host',
    voice: 'sol',
    realtimeModel: 'gpt-4o-realtime-preview-2024-12-17',
    instructions:
      "You are a poised female maître d' at an upscale international restaurant. Speak with a refined, lightly British accent, precise enunciation, and gracious warmth. Use elevated service phrases such as 'It would be my pleasure' and 'Allow me to arrange that for you'.",
  },
};

const DEFAULT_PERSONA = PERSONA_PRESETS.friendly_guide;

export async function POST(request: NextRequest) {
  try {
    const apiKey = process.env.OPENAI_API_KEY;
    
    if (!apiKey) {
      return NextResponse.json(
        { error: 'OPENAI_API_KEY not found in environment variables' },
        { status: 500 }
      );
    }

    let personaSelection: PersonaPreset = DEFAULT_PERSONA;
    try {
      const body = await request.json();
      if (body && typeof body.persona === 'string') {
        const key = body.persona.toLowerCase();
        if (PERSONA_PRESETS[key]) {
          personaSelection = PERSONA_PRESETS[key];
        }
      }
    } catch (error) {
      // Body might be empty or not JSON; fall back silently
    }

    // Create a new Realtime API session
    const response = await fetch('https://api.openai.com/v1/realtime/sessions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: personaSelection.realtimeModel,
        voice: personaSelection.voice,
        input_audio_format: 'pcm16',
        output_audio_format: 'pcm16',
        turn_detection: {
          type: 'server_vad',
        },
        instructions: personaSelection.instructions,
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
      persona: personaSelection.id,
      ws_url: `wss://api.openai.com/v1/realtime?model=${personaSelection.realtimeModel}`,
    });
    
  } catch (error: any) {
    console.error('Error creating session:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}


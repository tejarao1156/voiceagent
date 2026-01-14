"""
Feature Flags Configuration
Controls which features are visible in the UI.

States:
- "enabled"     : Feature fully visible and functional
- "coming_soon" : Tab visible with badge, content shows "Coming Soon"
- "disabled"    : Tab completely hidden

Always enabled (no flag needed):
- Dashboard, Settings, Prompts, Endpoints & Webhooks
"""

import os


def get_feature_flags():
    """Get all feature flags from environment variables"""
    return {
        # Main features
        "voice": os.getenv("FEATURE_VOICE", "enabled"),
        "ai_chat": os.getenv("FEATURE_AI_CHAT", "enabled"),
        "messaging": os.getenv("FEATURE_MESSAGING", "enabled"),
        "voice_customization": os.getenv("FEATURE_VOICE_CUSTOMIZATION", "enabled"),
        "campaigns": os.getenv("FEATURE_CAMPAIGNS", "enabled"),
        
        # Campaign sub-features (only apply when campaigns=enabled)
        "campaign_voice": os.getenv("FEATURE_CAMPAIGN_VOICE", "enabled"),
        "campaign_sms": os.getenv("FEATURE_CAMPAIGN_SMS", "enabled"),
        "campaign_whatsapp": os.getenv("FEATURE_CAMPAIGN_WHATSAPP", "enabled"),
    }


# Mapping: which sidebar tabs belong to which feature group
TAB_MAPPING = {
    "voice": ["incoming-agent", "logs"],
    "ai_chat": ["ai-chat", "ai-chat-logs"],
    "messaging": ["messaging-agents", "messages"],
    "voice_customization": ["voices"],
    "campaigns": ["campaigns"],
}

# Tabs that are always enabled (no flag check)
ALWAYS_ENABLED_TABS = ["dashboard", "settings", "prompts", "endpoints"]

# Voice Agent - Feature Flows

This folder contains documentation for all feature implementations in the Voice Agent system.

## Quick Links

| Flow | Description |
|------|-------------|
| [Voice Incoming](./voice-incoming.md) | Handling incoming phone calls |
| [Voice Outgoing](./voice-outgoing.md) | Making outbound calls (campaigns) |
| [SMS Incoming](./sms-incoming.md) | Receiving SMS messages |
| [SMS Outgoing](./sms-outgoing.md) | Sending SMS (including campaigns) |
| [WhatsApp Incoming](./whatsapp-incoming.md) | Receiving WhatsApp messages |
| [WhatsApp Outgoing](./whatsapp-outgoing.md) | Sending WhatsApp (including campaigns) |
| [Campaigns](./campaigns.md) | Campaign creation, execution & recovery |
| [Contact Lists](./contact-lists.md) | Contact list management & Excel upload |
| [AI Chat](./ai-chat.md) | Browser-based AI voice chat |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  Dashboard │ Campaigns │ Contact Lists │ AI Chat │ Settings     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  api_general.py - REST APIs, Webhooks, WebSocket                │
└────────┬────────────────────┬────────────────────┬──────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌────────────────┐  ┌─────────────────┐  ┌────────────────────────┐
│   Twilio       │  │   MongoDB       │  │   Campaign Worker      │
│  Voice/SMS/WA  │  │  campaigns      │  │   (Background Tasks)   │
│                │  │  contact_lists  │  │                        │
└────────────────┘  │  messages       │  └────────────────────────┘
                    │  call_logs      │
                    └─────────────────┘
```

## Key Database Collections

| Collection | Purpose |
|------------|---------|
| `campaigns` | Campaign metadata (name, type, config, status) |
| `campaign_items` | Individual phone numbers with status tracking |
| `campaign_executions` | Execution logs (sent/failed records) |
| `contact_lists` | Reusable contact list metadata |
| `contacts` | Individual contacts within lists |
| `messages` | SMS/WhatsApp conversation history |
| `call_logs` | Voice call records and transcripts |

# Database Structure & Data Flow

## Overview
The Voice Agent system uses **MongoDB** as its primary data store.  The following collections are defined in the `databases/` package and are accessed via the corresponding store classes:

- `mongodb_phone_store.py` – **registered_phone_numbers**
- `mongodb_prompt_store.py` – **prompts**
- `mongodb_scheduled_call_store.py` – **scheduled_calls**
- `mongodb_agent_store.py` – **agents** (used by the incoming‑agent flow)
- `mongodb_message_store.py` – **messages** (SMS / chat history)
- `mongodb_call_store.py` – **calls** (call logs & transcripts)

Each collection follows a **soft‑delete** pattern (`isDeleted: bool`) and timestamps (`created_at`, `updated_at`).  Below you will find the schema for each collection, the key parameters, and a Mermaid diagram that visualises the relationships and typical data flow.

---

## 1. `registered_phone_numbers`
**Store:** `MongoDBPhoneStore`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | MongoDB primary key |
| `uuid` | string | Unique identifier for the phone record |
| `phoneNumber` | string | E.164 formatted phone number (e.g. `+18668134984`) |
| `provider` | string | Currently only `twilio` is supported |
| `twilioAccountSid` | string | Twilio Account SID for this phone |
| `twilioAuthToken` | string | Twilio Auth Token (stored encrypted in production) |
| `userId` | string | ID of the user who owns this phone number |
| `isActive` | bool | Determines whether the number can be used for inbound/outbound calls |
| `isDeleted` | bool | Soft‑delete flag – the number is hidden from UI when `true` |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last update timestamp |

**Usage**
- **Incoming calls** – Twilio webhook sends the `To` number. The API looks up a document where `phoneNumber` matches and `isActive` is `true`.
- **Outgoing calls** – UI dropdowns list only numbers where `isDeleted === false`.
- **Phone management UI** – CRUD operations map directly to this store.

---

## 2. `prompts`
**Store:** `MongoDBPromptStore`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Primary key |
| `name` | string | Human‑readable name for the prompt |
| `content` | string | Full prompt text that will be sent to the LLM during an AI call |
| `phoneNumberId` | ObjectId | Reference to a document in **registered_phone_numbers** – the phone this prompt is associated with |
| `userId` | string | ID of the user who owns this prompt |
| `description` | string (optional) | Short description shown in the UI |
| `category` | string (default `general`) | Used for UI grouping (e.g., `sales`, `support`, `reminder`) |
| `isDeleted` | bool | Soft‑delete flag |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

**Usage**
- When scheduling an **AI** outgoing call, the UI filters prompts where `phoneNumberId` matches the selected **From** number.
- Prompt CRUD endpoints (`/api/prompts`) expose these fields.
- The `content` is passed to the LLM in the `/api/calls/outbound` flow.

---

## 3. `scheduled_calls`
**Store:** `MongoDBScheduledCallStore`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Primary key |
| `callType` | string (`ai` or `normal`) | Determines whether an AI prompt is used |
| `fromPhoneNumberId` | ObjectId | Reference to **registered_phone_numbers** – the caller ID |
| `toPhoneNumbers` | array of strings | Destination numbers (E.164 format) |
| `scheduledDateTime` | datetime | When the call should be executed |
| `userId` | string | ID of the user who scheduled this call |
| `promptId` | ObjectId (optional) | Reference to a **prompts** document – required when `callType === 'ai'` |
| `promptContent` | string (optional) | Cached copy of the prompt text at schedule time |
| `status` | string (`pending`, `completed`, `failed`) | Current execution state |
| `isDeleted` | bool | Soft‑delete flag |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

**Usage**
- UI **Outgoing Agent** view creates a document via `POST /api/scheduled-calls`.
- A background worker (not part of the demo) would poll for `status === 'pending'` and trigger the actual call.
- The `promptContent` field stores a snapshot of the prompt so that later edits do not affect already‑scheduled calls.

---

## 4. `agents`
**Store:** `MongoDBAgentStore`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Primary key |
| `name` | string | Agent name displayed in the UI |
| `phoneNumber` | string | Phone number the agent listens on (must exist in **registered_phone_numbers**) |
| `userId` | string | ID of the user who owns this agent |
| `direction` | string (`incoming` / `outgoing`) |
| `sttModel` | string | Speech‑to‑text model identifier (e.g., `whisper-1`) |
| `inferenceModel` | string | LLM model identifier (e.g., `gpt-4o-mini`) |
| `ttsModel` | string | Text‑to‑speech model identifier (e.g., `tts-1`) |
| `ttsVoice` | string | Voice name used for TTS |
| `systemPrompt` | string | System‑level instruction for the LLM |
| `greeting` | string | Initial spoken greeting when a call connects. If empty, a default greeting is used. |
| `temperature` | float | Sampling temperature for the LLM |
| `maxTokens` | int | Token limit for LLM responses |
| `active` | bool | Whether the agent is currently enabled |
| `isDeleted` | bool | Soft‑delete flag |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

**Usage**
- Incoming‑agent UI lists agents filtered by `direction === 'incoming'` and `isDeleted === false`.
- When Twilio forwards a call, the webhook looks up the agent by the `To` phone number and loads its configuration.

---

## 5. `messages`
**Store:** `MongoDBMessageStore`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Primary key |
| `messageSid` | string | Twilio Message SID (unique identifier) |
| `fromNumber` | string | Sender phone number |
| `toNumber` | string | Recipient phone number |
| `body` | string | Text content of the SMS/message |
| `agentId` | ObjectId (optional) | Reference to an **agents** document when the message is part of an agent conversation |
| `userId` | string | ID of the user associated with this message (via phone number) |
| `created_at` | datetime | Timestamp when the message was received/sent |
| `updated_at` | datetime | Timestamp of the last update |

**Usage**
- UI **Messages** view displays a conversation thread grouped by `fromNumber`/`toNumber`.
- Incoming SMS webhook stores each incoming message using this store.

---

## 6. `calls`
**Store:** `MongoDBCallStore`

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Primary key |
| `call_sid` | string | Twilio Call SID (unique identifier) |
| `from_number` | string | Caller's phone number |
| `to_number` | string | Callee's phone number (Twilio number) |
| `agent_id` | string | ID of the agent handling the call |
| `userId` | string | ID of the user who owns the agent/phone for this call |
| `session_id` | string | Unique session ID for the conversation |
| `status` | string | `active` (ongoing) or `completed` (finished) |
| `start_time` | datetime | When the call started |
| `end_time` | datetime (optional) | When the call ended |
| `duration_seconds` | float (optional) | Duration of the call in seconds |
| `transcript` | array of objects | List of `{role, text, timestamp}` messages |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Update timestamp |

**Usage**
- **Call Logs UI** – Displays a list of calls and their transcripts.
- **Real-time Updates** – Active calls are polled to show live transcripts.
- **Analytics** – Used to calculate call duration and agent performance.

---

## Data Flow Diagram
Below is a **Mermaid** diagram that visualises the typical flow of data between the collections during a call lifecycle.

```mermaid
flowchart TD
    subgraph UI
        A[User selects Phone] --> B[Prompts dropdown]
        B --> C[Schedule Outgoing Call]
        C --> D[POST /api/scheduled-calls]
    end

    subgraph Backend
        D --> E[MongoDB: scheduled_calls]
        E -->|stores| F[scheduled_calls document]
        F -->|references| G[registered_phone_numbers]
        F -->|optional| H[prompts]
        
        %% Incoming call flow
        I[Twilio webhook] --> J[Lookup phone in registered_phone_numbers]
        J --> K[Find agent (agents collection)]
        K --> L[Load agent config]
        L --> O[Create call record in calls collection]
        O --> M[Create conversation session]
        M --> N[Store messages in messages collection]
        M --> P[Update transcript in calls collection]
    end

    style UI fill:#e3f2fd,stroke:#90caf9,stroke-width:2px
    style Backend fill:#fff3e0,stroke:#ffb74d,stroke-width:2px
```

---

## How Parameters Are Used
| Parameter | Where It Lives | How It Is Consumed |
|-----------|----------------|-------------------|
| `phoneNumber` (registered_phone_numbers) | UI dropdowns, Twilio webhook | Determines the caller ID for outbound calls and routes inbound calls to the correct agent. |
| `promptId` / `promptContent` (prompts) | Outgoing‑Agent UI, scheduled_calls | `promptId` links a scheduled AI call to a prompt; `promptContent` is cached so the AI call uses the exact text at schedule time. |
| `callType` (scheduled_calls) | Outgoing‑Agent UI | Chooses between a normal Twilio call (`normal`) or an AI‑augmented call (`ai`). |
| `status` (scheduled_calls) | Scheduler / background worker | Tracks execution progress – `pending` → `completed` / `failed`. |
| `agentId` (messages) | SMS webhook & chat UI | Associates an SMS message with a specific agent for context‑aware replies. |
| `sttModel`, `inferenceModel`, `ttsModel`, `ttsVoice` (agents) | Incoming‑Agent runtime | Configures the speech‑to‑text, LLM, and text‑to‑speech pipelines for each live call. |
| `active` (agents) | Agents UI | Enables or disables an agent without deleting its configuration. |
| `call_sid` / `transcript` (calls) | Call Logs UI | Displays the history and content of past and active calls. |
| `userId` (all collections) | Auth & Multi-tenancy | Links every resource (phone, agent, call, prompt) to a specific registered user, enabling data isolation and user-specific views. |

---

## Adding New Collections
If you need to extend the system:
1. **Create a new store class** in `databases/` following the pattern of the existing stores.
2. **Add a collection** in MongoDB with the soft‑delete (`isDeleted`) and timestamp fields.
3. **Expose CRUD endpoints** in `api_general.py` using the same response schema (`{ success: true, ... }`).
4. **Update the UI** – add a new view component and navigation entry similar to `PromptsView` or `OutgoingAgentView`.

---

*This documentation lives in `docs/database_structure_and_flow.md` and can be rendered directly by the Next.js demo UI or any markdown viewer.*

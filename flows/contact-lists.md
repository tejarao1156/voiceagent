# Contact Lists Flow

Management of reusable contact lists with Excel upload support.

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Dashboard
    participant API as api_general.py
    participant Store as MongoDBContactListStore

    Note over User,Store: Create List
    User->>UI: Click "New List"
    User->>UI: Enter name + select Excel file
    UI->>API: POST /api/contact-lists {name}
    API->>Store: create_list()
    Store-->>API: list_id
    
    alt Excel file selected
        UI->>API: POST /api/contact-lists/{id}/upload
        Note over API: Parse Excel (openpyxl)
        Note over API: Find "Phone Number" column
        Note over API: Validate with process_phone_list()
        API->>Store: add_contacts()
    end
    
    Note over User,Store: Use in Campaign
    User->>UI: Create Campaign → "Use Existing List"
    UI->>API: POST /api/campaigns {contact_list_id}
    API->>Store: get_active_contacts_for_campaign()
    Note over Store: Returns array of valid phone numbers
```

## Excel File Format

| Column | Required | Description |
|--------|----------|-------------|
| Phone Number | ✅ Yes | Phone numbers (any format) |
| Name | ❌ Optional | Contact name |

The backend accepts any column containing "phone" in the header (case-insensitive).

## Key Files

| File | Purpose |
|------|---------|
| [mongodb_contact_list_store.py](../databases/mongodb_contact_list_store.py) | CRUD operations |
| [phone_validator.py](../utils/phone_validator.py) | Phone number validation |
| [api_general.py](../api_general.py) | Upload endpoint |

## Database Schema

### `contact_lists` Collection
```json
{
  "_id": ObjectId,
  "name": "VIP Customers",
  "userId": "user123",
  "contact_count": 500,
  "version": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

### `contacts` Collection
```json
{
  "_id": ObjectId,
  "list_id": ObjectId,
  "phone_number": "+15551234567",
  "normalized_phone": "+15551234567",
  "name": "John Doe",
  "status": "active|invalid"
}
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/contact-lists` | List all contact lists |
| POST | `/api/contact-lists` | Create new list |
| POST | `/api/contact-lists/{id}/upload` | Upload Excel file |
| GET | `/api/contact-lists/{id}/contacts` | Get contacts in list |
| DELETE | `/api/contact-lists/{id}` | Delete list |

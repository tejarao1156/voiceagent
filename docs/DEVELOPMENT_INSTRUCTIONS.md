# Development Instructions for AI Assistant

This file contains instructions that the AI assistant should follow for every code change request. **Users can modify these instructions** to customize the development workflow.

## Core Principles

1. **Minimal Changes**: Only modify code that is necessary for the requested feature. Don't change unrelated code.
2. **Reuse Existing Code**: Before creating new functions, check if existing functions or features can be reused.
3. **Test Everything**: Test all features that are changed. If you change a function within a feature, test the entire feature.
4. **Maintain Existing Flow**: Don't break existing functionality. If changes are required, make them carefully and test thoroughly.
5. never add dummy data into ui for the testing
6. when user asks to build something consider all the edge cases so that no error can occur for ui and backend

## Workflow for Every Request

### 1. Understanding the Request
- Read the user's request carefully
- Identify what needs to be changed
- Check if similar functionality already exists
- Determine if existing code can be reused

### 2. Planning Changes
- List all files that need to be modified
- Identify functions/features that can be reused
- Plan the minimal set of changes required
- Consider backward compatibility

### 3. Implementation
- Make changes only to necessary files
- Reuse existing functions where possible
- Follow existing code patterns and style
- Add proper error handling
- Add logging where appropriate

### 4. Testing
- Test all modified functions
- Test the entire feature if any function in it was changed
- Verify integration with other components
- Check for linting errors
- Verify the complete flow works end-to-end

### 5. Verification
- Run comprehensive tests
- Verify no existing functionality is broken
- Check that all features work as expected
- Document any important changes

## Specific Guidelines

### Code Changes
- ✅ DO: Make minimal, targeted changes
- ✅ DO: Reuse existing functions/classes
- ✅ DO: Follow existing code patterns
- ✅ DO: Add error handling and logging
- ❌ DON'T: Change unrelated code
- ❌ DON'T: Create duplicate functionality
- ❌ DON'T: Break existing features

### Testing Requirements
- ✅ Test all modified functions
- ✅ Test the complete feature if any part is changed
- ✅ Test integration with other components
- ✅ Verify error handling works
- ✅ Check for edge cases

### File Organization
- Keep related code together
- Follow existing file structure
- Use appropriate file locations
- Maintain consistent naming conventions

### Error Handling
- Add try-except blocks where needed
- Log errors appropriately
- Provide meaningful error messages
- Handle edge cases gracefully

### Logging
- Use appropriate log levels (debug, info, warning, error)
- Include relevant context in log messages
- Log important state changes
- Log errors with full details

## Example Workflow

### Request: "Add feature X to component Y"

1. **Understand**: What is feature X? Where is component Y?
2. **Check**: Does similar functionality exist? Can it be reused?
3. **Plan**: What files need changes? What functions can be reused?
4. **Implement**: Make minimal changes, reuse existing code
5. **Test**: Test feature X, test component Y, test integration
6. **Verify**: Everything works, nothing is broken

## Notes

- These instructions can be modified by users
- Follow the spirit of these instructions, not just the letter
- When in doubt, ask for clarification
- Prioritize code quality and maintainability


## End-to-End (E2E) Testing Rules

These rules define the standard operating procedure for AI agents (and human developers) when creating and executing E2E tests for the Voice Agent platform.

### 1. Environment & Isolation
*   **Fresh User Principle**: NEVER reuse a hardcoded email address. Always generate a unique email for each test run (e.g., using a timestamp: `test_user_$(date +%s)@test.com`). This prevents state pollution from previous runs.
*   **Service Check**: Before running tests, verify that the core services are up:
    *   FastAPI Backend (`http://localhost:4002/health` or similar)
    *   MongoDB (Connection check)
    *   Ngrok (if testing callbacks/webhooks)

### 2. Authentication Flow
*   **Full Flow Verification**: Do not mock authentication.
    1.  **Register**: `POST /auth/register` with the fresh email.
    2.  **Login**: `POST /auth/login` to retrieve the token.
    3.  **Token Extraction**: Extract the JWT token from the JSON response.
*   **Header Usage**: Use the extracted token in the `Cookie` header (`Cookie: auth_token=$TOKEN`) for all subsequent authenticated requests.

### 3. Resource Management & Dependencies
*   **Logical Order**: Create resources in the order of dependency.
    *   *Example*: `Create Prompt` -> `Register Phone` -> `Create Agent (using Prompt & Phone)` -> `Schedule Call`.
*   **ID Propagation**: Capture the ID (e.g., `prompt_id`, `agent_id`) from the creation response and use it dynamically in subsequent steps. Never hardcode IDs.

### 4. Verification Standards
*   **Step-by-Step Validation**: Verify success *immediately* after each step.
    *   *HTTP Status*: Ensure 200/201.
    *   *Response Body*: Check for `success: true` or valid ID fields.
*   **Deep Verification**: Do not just check if an object was created. Verify its **content**.
    *   *Example*: If you created a prompt with `introduction: "Hello"`, fetch the created prompt (or the agent using it) and assert that `introduction == "Hello"`.
*   **Cross-Resource Verification**: If Resource A affects Resource B (e.g., Prompt affects Agent's greeting), verify the change in Resource B.

### 5. Error Handling & Debugging
*   **Fail Fast**: If a critical step fails (e.g., Auth fails, Resource creation fails), **EXIT IMMEDIATELY**. Do not continue.
*   **Verbose Failure Logs**: On failure, print:
    *   The HTTP Status Code.
    *   The **Full Response Body** (JSON).
    *   The Payload sent (if relevant).
*   **Logs**: Capture server logs (`/tmp/server.log`) if a 500 error occurs.

### 6. Cleanup
*   **Success Cleanup**: If the test passes, remove all temporary files (scripts, cookie files, logs) to keep the workspace clean.
*   **Failure Preservation**: If the test fails, **KEEP** the temporary files and logs for debugging.

### 7. Scripting Best Practices
*   **Language**: Bash scripts using `curl` and `python3` (for JSON parsing) are preferred for portability and speed.
*   **JSON Parsing**: Use `python3 -c "import sys, json; ..."` to robustly parse JSON responses. Do not use `grep` or `sed` for JSON.
*   **Timeouts**: Allow sufficient wait time for async operations (e.g., server restart, webhook propagation), but set reasonable timeouts for curl commands.


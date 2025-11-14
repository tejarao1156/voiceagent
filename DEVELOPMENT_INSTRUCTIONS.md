# Development Instructions for AI Assistant

This file contains instructions that the AI assistant should follow for every code change request. **Users can modify these instructions** to customize the development workflow.

## Core Principles

1. **Minimal Changes**: Only modify code that is necessary for the requested feature. Don't change unrelated code.
2. **Reuse Existing Code**: Before creating new functions, check if existing functions or features can be reused.
3. **Test Everything**: Test all features that are changed. If you change a function within a feature, test the entire feature.
4. **Maintain Existing Flow**: Don't break existing functionality. If changes are required, make them carefully and test thoroughly.

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


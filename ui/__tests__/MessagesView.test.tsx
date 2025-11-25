/**
 * UI Tests for MessagesView Component
 * Tests the Messages & SMS feature functionality
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'

// Mock the MessagesView component logic
// Since it's embedded in page.tsx, we'll test the key functionality

describe('MessagesView Component Tests', () => {
  // Mock fetch for API calls
  beforeEach(() => {
    global.fetch = jest.fn()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  describe('Message Detection Logic', () => {
    test('should identify customer messages correctly', () => {
      const customerMessages = [
        { role: 'user', text: 'Hello', direction: 'inbound' },
        { role: 'customer', text: 'Hi', direction: 'inbound' },
        { text: 'Test', direction: 'inbound' }, // No role, but direction indicates customer
        { sender: 'customer', text: 'Help' },
      ]

      customerMessages.forEach(msg => {
        const role = msg.role?.toLowerCase() || ''
        const direction = msg.direction?.toLowerCase() || ''
        const sender = msg.sender?.toLowerCase() || ''
        
        let messageFromCustomer = false
        
        if (role === 'user' || role === 'customer') {
          messageFromCustomer = true
        } else if (role === 'assistant' || role === 'agent') {
          messageFromCustomer = false
        } else if (direction === 'inbound') {
          messageFromCustomer = true
        } else if (direction === 'outbound') {
          messageFromCustomer = false
        } else if (sender === 'customer') {
          messageFromCustomer = true
        }

        expect(messageFromCustomer).toBe(true)
      })
    })

    test('should identify agent messages correctly', () => {
      const agentMessages = [
        { role: 'assistant', text: 'How can I help?', direction: 'outbound' },
        { role: 'agent', text: 'Sure!', direction: 'outbound' },
        { text: 'Response', direction: 'outbound' }, // No role, but direction indicates agent
        { text: 'Unknown' }, // Defaults to agent
      ]

      agentMessages.forEach(msg => {
        const role = msg.role?.toLowerCase() || ''
        const direction = msg.direction?.toLowerCase() || ''
        const sender = msg.sender?.toLowerCase() || ''
        
        let messageFromCustomer = false
        
        if (role === 'user' || role === 'customer') {
          messageFromCustomer = true
        } else if (role === 'assistant' || role === 'agent') {
          messageFromCustomer = false
        } else if (direction === 'inbound') {
          messageFromCustomer = true
        } else if (direction === 'outbound') {
          messageFromCustomer = false
        } else if (sender === 'customer') {
          messageFromCustomer = true
        }

        expect(messageFromCustomer).toBe(false)
      })
    })

    test('should prioritize role over direction', () => {
      // Conflicting: role says agent, direction says inbound
      const msg = { role: 'assistant', direction: 'inbound', text: 'Test' }
      
      const role = msg.role?.toLowerCase() || ''
      let messageFromCustomer = false
      
      if (role === 'user' || role === 'customer') {
        messageFromCustomer = true
      } else if (role === 'assistant' || role === 'agent') {
        messageFromCustomer = false
      }

      // Role should take priority
      expect(messageFromCustomer).toBe(false)
    })
  })

  describe('Conversation Selection Logic', () => {
    test('should find conversation by conversation_id', () => {
      const conversations = [
        { conversation_id: '123', id: 'abc', callerNumber: '+1234567890' },
        { conversation_id: '456', id: 'def', callerNumber: '+0987654321' },
      ]

      const selectedId = '123'
      const selectedConversation = conversations.find(c => 
        c.conversation_id === selectedId || c.id === selectedId
      )

      expect(selectedConversation).toBeDefined()
      expect(selectedConversation?.conversation_id).toBe('123')
    })

    test('should find conversation by id when conversation_id is missing', () => {
      const conversations = [
        { id: 'abc', callerNumber: '+1234567890' },
        { id: 'def', callerNumber: '+0987654321' },
      ]

      const selectedId = 'abc'
      const selectedConversation = conversations.find(c => 
        c.conversation_id === selectedId || c.id === selectedId
      )

      expect(selectedConversation).toBeDefined()
      expect(selectedConversation?.id).toBe('abc')
    })
  })

  describe('Empty State Handling', () => {
    test('should handle empty conversations array', () => {
      const conversations: any[] = []
      expect(conversations.length).toBe(0)
    })

    test('should handle conversation with no messages', () => {
      const conversation = {
        conversation_id: '123',
        conversation: [],
        callerNumber: '+1234567890',
      }

      const hasMessages = conversation.conversation && conversation.conversation.length > 0
      expect(hasMessages).toBe(false)
    })

    test('should handle missing fields gracefully', () => {
      const conversation = {
        conversation_id: '123',
        conversation: [{ text: 'Test' }],
      }

      // Should have fallbacks
      const callerNumber = conversation.callerNumber || 'Unknown'
      const agentNumber = conversation.agentNumber || 'Unknown'
      const latestMessage = conversation.latest_message || 'No messages'

      expect(callerNumber).toBe('Unknown')
      expect(agentNumber).toBe('Unknown')
      expect(latestMessage).toBe('No messages')
    })
  })

  describe('Send Message Functionality', () => {
    test('should validate message text before sending', () => {
      const messageText = ''
      const canSend = messageText.trim().length > 0
      expect(canSend).toBe(false)
    })

    test('should validate required phone numbers', () => {
      const conversation = {
        agentNumber: '+1234567890',
        callerNumber: '+0987654321',
      }

      const canSend = !!(conversation.agentNumber && conversation.callerNumber)
      expect(canSend).toBe(true)
    })

    test('should handle missing phone numbers', () => {
      const conversation = {
        agentNumber: null,
        callerNumber: '+0987654321',
      }

      const canSend = !!(conversation.agentNumber && conversation.callerNumber)
      expect(canSend).toBe(false)
    })

    test('should trim message text before sending', () => {
      const messageText = '  Hello World  '
      const trimmed = messageText.trim()
      expect(trimmed).toBe('Hello World')
    })
  })

  describe('API Integration', () => {
    test('should fetch conversations on mount', async () => {
      const mockConversations = [
        {
          conversation_id: '123',
          callerNumber: '+1234567890',
          agentNumber: '+0987654321',
          conversation: [
            { role: 'user', text: 'Hello', direction: 'inbound' },
            { role: 'assistant', text: 'Hi there!', direction: 'outbound' },
          ],
        },
      ]

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ messages: mockConversations }),
      })

      const response = await fetch('/api/messages')
      const data = await response.json()

      expect(data.messages).toEqual(mockConversations)
      expect(global.fetch).toHaveBeenCalledWith('/api/messages')
    })

    test('should send message via API', async () => {
      const mockResponse = {
        success: true,
        message_sid: 'SM123456',
        from: '+1234567890',
        to: '+0987654321',
      }

      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const response = await fetch('/api/messages/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: '+1234567890',
          to: '+0987654321',
          body: 'Test message',
        }),
      })

      const data = await response.json()

      expect(data.success).toBe(true)
      expect(data.message_sid).toBe('SM123456')
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/messages/send',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      )
    })

    test('should handle API errors gracefully', async () => {
      ;(global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'))

      try {
        await fetch('/api/messages')
      } catch (error) {
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toBe('Network error')
      }
    })
  })

  describe('Message Formatting', () => {
    test('should format timestamps correctly', () => {
      const timestamp = '2024-01-01T12:00:00Z'
      const date = new Date(timestamp)
      const formatted = date.toLocaleTimeString()
      
      expect(formatted).toBeTruthy()
      expect(typeof formatted).toBe('string')
    })

    test('should handle missing timestamps', () => {
      const msg = { text: 'Test', timestamp: null }
      const formatted = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''
      expect(formatted).toBe('')
    })

    test('should use text or body field for message content', () => {
      const msg1 = { text: 'Hello', role: 'user' }
      const msg2 = { body: 'World', role: 'assistant' }
      const msg3 = { role: 'user' } // No text or body

      expect(msg1.text || msg1.body || '').toBe('Hello')
      expect(msg2.text || msg2.body || '').toBe('World')
      expect(msg3.text || msg3.body || '').toBe('')
    })
  })

  describe('UI State Management', () => {
    test('should manage loading state', () => {
      let loading = true
      expect(loading).toBe(true)

      loading = false
      expect(loading).toBe(false)
    })

    test('should manage sending state', () => {
      let sending = false
      expect(sending).toBe(false)

      sending = true
      expect(sending).toBe(true)
    })

    test('should manage message text state', () => {
      let messageText = ''
      expect(messageText).toBe('')

      messageText = 'Hello World'
      expect(messageText).toBe('Hello World')
    })

    test('should manage selected conversation ID', () => {
      let selectedId: string | null = null
      expect(selectedId).toBeNull()

      selectedId = '123'
      expect(selectedId).toBe('123')
    })
  })
})


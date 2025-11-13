import { useEffect, useRef, useState } from 'react'

export function useWebSocket<T = any>(
  url: string | null,
  onMessage?: (data: T) => void
) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<T | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!url) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setLastMessage(data)
        onMessage?.(data)
      } catch (e) {
        console.error('Error parsing WebSocket message:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [url, onMessage])

  return { isConnected, lastMessage, send: (data: any) => wsRef.current?.send(JSON.stringify(data)) }
}


import { useEffect, useRef, useCallback, useState } from 'react'

interface WebSocketMessage {
  type: string
  data?: Record<string, unknown>
  source?: string
  timestamp?: string
  message?: string
}

interface UseWebSocketOptions {
  url?: string
  token?: string
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

interface UseWebSocketReturn {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  sendMessage: (message: Record<string, unknown>) => void
  reconnect: () => void
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
    token,
    onMessage,
    onConnect,
    onDisconnect,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  const connect = useCallback(() => {
    if (!token) return

    try {
      const wsUrl = `${url}?token=${token}`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setIsConnected(true)
        reconnectCountRef.current = 0
        onConnect?.()
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          onMessage?.(message)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        onDisconnect?.()

        // Auto-reconnect
        if (reconnectCountRef.current < maxReconnectAttempts) {
          reconnectTimerRef.current = setTimeout(() => {
            reconnectCountRef.current++
            connect()
          }, reconnectInterval)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }, [token, url, onMessage, onConnect, onDisconnect, reconnectInterval, maxReconnectAttempts])

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const reconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
    }
    wsRef.current?.close()
    reconnectCountRef.current = 0
    connect()
  }, [connect])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
      }
      wsRef.current?.close()
    }
  }, [connect])

  // Send periodic ping to keep connection alive
  useEffect(() => {
    if (!isConnected) return

    const pingInterval = setInterval(() => {
      sendMessage({ type: 'ping' })
    }, 30000)

    return () => clearInterval(pingInterval)
  }, [isConnected, sendMessage])

  return { isConnected, lastMessage, sendMessage, reconnect }
}

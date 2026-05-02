import type { SSEEvent } from '../types/generated'

type EventHandler = (event: SSEEvent) => void

export class SSEClient {
  private eventSource: EventSource | null = null
  private handlers: EventHandler[] = []

  connect(interviewId: string) {
    this.disconnect()

    const url = `${import.meta.env.VITE_API_URL || ''}/interview/${interviewId}/stream`
    this.eventSource = new EventSource(url)

    this.eventSource.onmessage = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as SSEEvent
        this.handlers.forEach((h) => h(data))
      } catch {
        // ignore parse errors
      }
    }

    this.eventSource.onerror = () => {
      // EventSource auto-reconnects; handlers can detect errors via status events
    }
  }

  onEvent(handler: EventHandler) {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler)
    }
  }

  disconnect() {
    this.eventSource?.close()
    this.eventSource = null
  }
}

export const sseClient = new SSEClient()

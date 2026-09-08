import { useMemo, useState } from 'react'
import type { Message } from '@ag-ui/client'

import { createChatAgent, type ChatAgent } from '../api/chatApi'

interface ChatFormProps {
  /** Overridable for tests — defaults to a real HttpAgent-backed agent. */
  createAgent?: (threadId: string) => ChatAgent
}

export function ChatForm({ createAgent = createChatAgent }: ChatFormProps) {
  const agent = useMemo(() => createAgent(crypto.randomUUID()), [createAgent])
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = message
    setMessage('')
    setLoading(true)

    agent.addMessage({ id: crypto.randomUUID(), role: 'user', content: text })
    setMessages([...agent.messages])

    try {
      await agent.runAgent(
        {},
        { onMessagesChanged: ({ messages: updated }) => setMessages([...updated]) },
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={{ maxWidth: 480, margin: '4rem auto', textAlign: 'center' }}>
      <h1>langgraph-poc</h1>
      <ul style={{ listStyle: 'none', padding: 0, textAlign: 'left' }}>
        {messages.map((m) => (
          <li key={m.id}>
            <strong>{m.role}: </strong>
            {typeof m.content === 'string' ? m.content : ''}
          </li>
        ))}
      </ul>
      <form onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Say something"
        />
        <button type="submit" disabled={loading || !message}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </section>
  )
}

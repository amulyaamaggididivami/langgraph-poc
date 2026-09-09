import { useState } from 'react'
import type { Message } from '@ag-ui/client'

import type { ChatAgent } from '../api/chatApi'
import { PREDEFINED_QUESTIONS } from '../constants'

interface ChatFormProps {
  agent: ChatAgent
  messages: Message[]
  onMessagesChange: (messages: Message[]) => void
}

export function ChatForm({ agent, messages, onMessagesChange }: ChatFormProps) {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = message
    setMessage('')
    setLoading(true)

    agent.addMessage({ id: crypto.randomUUID(), role: 'user', content: text })
    onMessagesChange([...agent.messages])

    try {
      await agent.runAgent(
        {},
        { onMessagesChanged: ({ messages: updated }) => onMessagesChange([...updated]) },
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={{ maxWidth: 560, margin: '0 auto', padding: '2rem 1rem', textAlign: 'center' }}>
      <h1>langgraph-poc</h1>
      <ul style={{ listStyle: 'none', padding: 0, textAlign: 'left' }}>
        {messages.map((m) => (
          <li key={m.id}>
            <strong>{m.role}: </strong>
            {typeof m.content === 'string' ? m.content : ''}
          </li>
        ))}
      </ul>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
        {PREDEFINED_QUESTIONS.map((q) => (
          <button key={q} type="button" onClick={() => setMessage(q)}>
            {q}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Say something"
          style={{ width: '70%' }}
        />
        <button type="submit" disabled={loading || !message}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </section>
  )
}

import { useState } from 'react'

import { sendMessage } from '../api/chatApi'

export function ChatForm() {
  const [message, setMessage] = useState('')
  const [reply, setReply] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await sendMessage(message)
      setReply(data.reply)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={{ maxWidth: 480, margin: '4rem auto', textAlign: 'center' }}>
      <h1>langgraph-poc</h1>
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
      {reply && <p>Reply: {reply}</p>}
    </section>
  )
}

import { useState } from 'react'
import type { Message } from '@ag-ui/client'

import { createChatAgent } from './api/chatApi'
import { ChatForm } from './components/ChatForm'
import { ReviewPage } from './components/ReviewPage'
import './App.css'

// Every question goes through review before it's ever delivered, so
// Chat and Review live on one page, not separate routes — approving in
// Review needs to show up in the same Chat pane immediately, not after
// navigating back to it.
function App() {
  const [agent] = useState(() => createChatAgent(crypto.randomUUID()))
  const [messages, setMessages] = useState<Message[]>([])

  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'stretch' }}>
      <div style={{ flex: '0 0 70%', minWidth: 0 }}>
        <ChatForm agent={agent} messages={messages} onMessagesChange={setMessages} />
      </div>
      <div style={{ flex: '0 0 30%', minWidth: 0, borderLeft: '1px solid var(--border)' }}>
        <ReviewPage
          onResumed={(threadId, resumedMessages) => {
            // Only the thread Chat currently has open should update —
            // a decision on any other pending thread stays in the queue.
            if (threadId === agent.threadId) setMessages(resumedMessages)
          }}
        />
      </div>
    </div>
  )
}

export default App

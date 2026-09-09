import { useState } from 'react'
import type { Message } from '@ag-ui/client'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { ChatAgent } from '../api/chatApi'
import { ChatForm } from './ChatForm'

// TASK-ORCHESTRATION-010 / TEST-ORCHESTRATION-027: a fake standing in for
// the mocked SSE stream — it captures the `onMessagesChanged` subscriber
// ChatForm registers with runAgent, so the test can feed it a sequence
// of message-array snapshots one at a time, exactly like real streamed
// BaseEvents would drive it, without needing a real SSE mock.
function makeFakeAgent() {
  const messages: Message[] = []
  let onMessagesChanged: ((params: { messages: Message[] }) => void) | undefined

  const agent: ChatAgent = {
    threadId: 'fake-thread-id',
    messages,
    addMessage(m) {
      messages.push(m)
    },
    setMessages(m) {
      messages.length = 0
      messages.push(...m)
    },
    async runAgent(_params, subscriber) {
      onMessagesChanged = subscriber?.onMessagesChanged as typeof onMessagesChanged
      return { result: undefined, newMessages: [] }
    },
  }

  return {
    agent,
    emit(step: Message[]) {
      messages.length = 0
      messages.push(...step)
      onMessagesChanged?.({ messages: [...messages] })
    },
  }
}

// ChatForm is a controlled component now (App.tsx owns `messages` so it
// can also be updated from ReviewPage's resume) — this harness plays
// App.tsx's role of holding that state for the test.
function ControlledChatForm({ agent }: { agent: ChatAgent }) {
  const [messages, setMessages] = useState<Message[]>([])
  return <ChatForm agent={agent} messages={messages} onMessagesChange={setMessages} />
}

describe('ChatForm', () => {
  it('renders each streamed update in order, ending on the final response', async () => {
    const user = userEvent.setup()
    const fake = makeFakeAgent()

    render(<ControlledChatForm agent={fake.agent} />)

    await user.type(screen.getByPlaceholderText('Say something'), 'total sales?')
    await user.click(screen.getByRole('button', { name: /send/i }))

    act(() => {
      fake.emit([
        { id: 'u1', role: 'user', content: 'total sales?' },
        { id: 'a1', role: 'assistant', content: 'Thinking...' },
      ])
    })
    expect(screen.getByText(/Thinking\.\.\./)).toBeInTheDocument()

    act(() => {
      fake.emit([
        { id: 'u1', role: 'user', content: 'total sales?' },
        { id: 'a1', role: 'assistant', content: 'The total is $476,750.' },
      ])
    })
    expect(screen.getByText(/The total is \$476,750\./)).toBeInTheDocument()
    expect(screen.queryByText(/Thinking\.\.\./)).not.toBeInTheDocument()
  })
})

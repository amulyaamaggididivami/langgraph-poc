import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { AguiEvent, PendingReview, ReviewApi } from '../api/reviewApi'
import { ReviewPage } from './ReviewPage'

function makeFakeReviewApi(initial: PendingReview[]) {
  let pending = initial
  const decideCalls: { threadId: string; decision: 'approve' | 'reject' }[] = []
  let nextEvents: AguiEvent[] = []
  let nextShouldFail: Error | null = null

  const api: ReviewApi = {
    async listPending() {
      return pending
    },
    async decide(threadId, decision, onEvent) {
      decideCalls.push({ threadId, decision })
      if (nextShouldFail) {
        const err = nextShouldFail
        nextShouldFail = null
        throw err
      }
      for (const event of nextEvents) onEvent?.(event)
      pending = pending.filter((row) => row.thread_id !== threadId)
    },
  }

  return {
    api,
    decideCalls,
    setNextEvents(events: AguiEvent[]) {
      nextEvents = events
    },
    setNextFailure(err: Error) {
      nextShouldFail = err
    },
    setPending(rows: PendingReview[]) {
      pending = rows
    },
  }
}

const SAMPLE: PendingReview = {
  thread_id: '11111111-1111-1111-1111-111111111111',
  question_text: 'what were total sales last month?',
  updated_at: '2026-09-08T12:00:00Z',
}

describe('ReviewPage', () => {
  it('shows an empty state when nothing is pending', async () => {
    const fake = makeFakeReviewApi([])
    render(<ReviewPage reviewApi={fake.api} />)

    expect(await screen.findByText(/nothing is awaiting review/i)).toBeInTheDocument()
  })

  it('lists a pending item and approves it', async () => {
    const user = userEvent.setup()
    const fake = makeFakeReviewApi([SAMPLE])
    fake.setNextEvents([{ type: 'TEXT_MESSAGE_CONTENT', delta: 'Total sales were $476,750.' }])

    render(<ReviewPage reviewApi={fake.api} />)

    expect(await screen.findByText(SAMPLE.question_text)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /approve/i }))

    expect(await screen.findByText('Delivered')).toBeInTheDocument()
    expect(screen.getByText('Total sales were $476,750.')).toBeInTheDocument()
    expect(fake.decideCalls).toEqual([{ threadId: SAMPLE.thread_id, decision: 'approve' }])
  })

  it('rejects an item and shows it as withheld', async () => {
    const user = userEvent.setup()
    const fake = makeFakeReviewApi([SAMPLE])

    render(<ReviewPage reviewApi={fake.api} />)
    await screen.findByText(SAMPLE.question_text)

    await user.click(screen.getByRole('button', { name: /reject/i }))

    expect(await screen.findByText('Withheld')).toBeInTheDocument()
  })

  it('shows an error when the decision fails (e.g. already_decided)', async () => {
    const user = userEvent.setup()
    const fake = makeFakeReviewApi([SAMPLE])
    fake.setNextFailure(new Error('Thread is already Delivered, not AwaitingReview'))

    render(<ReviewPage reviewApi={fake.api} />)
    await screen.findByText(SAMPLE.question_text)

    await user.click(screen.getByRole('button', { name: /approve/i }))

    expect(await screen.findByText(/already delivered/i)).toBeInTheDocument()
  })

  it('shows a load error when the pending list request fails', async () => {
    const failingApi: ReviewApi = {
      listPending: vi.fn().mockRejectedValue(new Error('backend unreachable')),
      decide: vi.fn(),
    }

    render(<ReviewPage reviewApi={failingApi} />)

    expect(await screen.findByText('backend unreachable')).toBeInTheDocument()
  })

  it('refresh button reloads the pending list', async () => {
    const user = userEvent.setup()
    const fake = makeFakeReviewApi([SAMPLE])
    render(<ReviewPage reviewApi={fake.api} />)
    await screen.findByText(SAMPLE.question_text)

    await user.click(screen.getByRole('button', { name: /^refresh$/i }))

    await waitFor(() => expect(screen.getByText(SAMPLE.question_text)).toBeInTheDocument())
  })

  it('calls onResumed with the MESSAGES_SNAPSHOT event so Chat can show the delivered answer', async () => {
    const user = userEvent.setup()
    const fake = makeFakeReviewApi([SAMPLE])
    const snapshotMessages = [
      { id: 'm1', role: 'user' as const, content: SAMPLE.question_text },
      { id: 'a1', role: 'assistant' as const, content: 'Total sales were $476,750.' },
    ]
    fake.setNextEvents([
      { type: 'TEXT_MESSAGE_CONTENT', delta: 'Total sales were $476,750.' },
      { type: 'MESSAGES_SNAPSHOT', messages: snapshotMessages },
    ])
    const onResumed = vi.fn()

    render(<ReviewPage reviewApi={fake.api} onResumed={onResumed} />)
    await screen.findByText(SAMPLE.question_text)

    await user.click(screen.getByRole('button', { name: /approve/i }))

    await waitFor(() => expect(onResumed).toHaveBeenCalledWith(SAMPLE.thread_id, snapshotMessages))
  })

  it('a second cycle on the same thread_id shows as pending again, not stuck on the first decision', async () => {
    // Regression test: a thread_id is one whole conversation, not one
    // question — a follow-up question on an already-decided thread
    // reappears in the pending list under the *same* thread_id. It must
    // render with fresh Approve/Reject buttons, not the previous
    // decision's "Delivered"/"Withheld" label.
    const user = userEvent.setup()
    const fake = makeFakeReviewApi([SAMPLE])

    render(<ReviewPage reviewApi={fake.api} />)
    await screen.findByText(SAMPLE.question_text)
    await user.click(screen.getByRole('button', { name: /approve/i }))
    expect(await screen.findByText('Delivered')).toBeInTheDocument()

    const secondCycle: PendingReview = { ...SAMPLE, question_text: 'what about 2024' }
    fake.setPending([secondCycle])
    await user.click(screen.getByRole('button', { name: /^refresh$/i }))

    await screen.findByText('what about 2024')
    expect(screen.queryByText('Delivered')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
  })
})

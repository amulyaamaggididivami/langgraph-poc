import { useEffect, useState } from 'react'
import type { Message } from '@ag-ui/client'

import { reviewApi as defaultReviewApi, type PendingReview, type ReviewApi } from '../api/reviewApi'

interface ReviewPageProps {
  /** Overridable for tests — defaults to the real fetch-backed client. */
  reviewApi?: ReviewApi
  /** Called with the resumed thread's full message history once a
   * decision completes — lets the page holding both ChatForm and
   * ReviewPage show the delivered/withheld answer in Chat, without
   * ReviewPage needing to know whether that thread is the one Chat has
   * open. */
  onResumed?: (threadId: string, messages: Message[]) => void
}

type Decision = 'approve' | 'reject'

interface ItemState {
  status: 'idle' | 'deciding' | 'done' | 'error'
  outcome?: Decision
  message?: string
  error?: string
}

export function ReviewPage({ reviewApi = defaultReviewApi, onResumed }: ReviewPageProps) {
  const [items, setItems] = useState<PendingReview[]>([])
  const [itemState, setItemState] = useState<Record<string, ItemState>>({})
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    setLoadError(null)
    try {
      setItems(await reviewApi.listPending())
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Could not load the review queue.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function decide(threadId: string, decision: Decision) {
    setItemState((prev) => ({ ...prev, [threadId]: { status: 'deciding' } }))
    let message = ''
    let snapshot: Message[] | null = null
    try {
      await reviewApi.decide(threadId, decision, (event) => {
        if (event.type === 'TEXT_MESSAGE_CONTENT' && typeof event.delta === 'string') {
          message += event.delta
        }
        if (event.type === 'MESSAGES_SNAPSHOT' && Array.isArray(event.messages)) {
          snapshot = event.messages
        }
      })
      setItemState((prev) => ({ ...prev, [threadId]: { status: 'done', outcome: decision, message } }))
      if (snapshot) onResumed?.(threadId, snapshot)
      setTimeout(refresh, 800)
    } catch (e) {
      setItemState((prev) => ({
        ...prev,
        [threadId]: { status: 'error', error: e instanceof Error ? e.message : 'The decision failed.' },
      }))
    }
  }

  return (
    <section style={{ padding: '2rem 1rem' }}>
      <h1 style={{ fontSize: '1.25rem' }}>Review queue</h1>
      <button onClick={refresh} disabled={loading}>
        {loading ? 'Refreshing…' : 'Refresh'}
      </button>

      {loadError && <p style={{ color: 'crimson' }}>{loadError}</p>}
      {!loading && !loadError && items.length === 0 && <p>Nothing is awaiting review.</p>}

      <ul style={{ listStyle: 'none', padding: 0 }}>
        {items.map((item) => {
          const state = itemState[item.thread_id] ?? { status: 'idle' as const }
          return (
            <li
              key={item.thread_id}
              style={{ border: '1px solid #ccc', borderRadius: 8, padding: '0.75rem', marginBottom: '0.75rem' }}
            >
              <div style={{ fontSize: '0.9rem' }}>{item.question_text}</div>
              <div style={{ fontSize: '0.7rem', color: '#666', wordBreak: 'break-all' }}>{item.thread_id}</div>

              {state.status === 'idle' && (
                <div style={{ marginTop: '0.5rem' }}>
                  <button onClick={() => decide(item.thread_id, 'approve')}>Approve</button>{' '}
                  <button onClick={() => decide(item.thread_id, 'reject')}>Reject</button>
                </div>
              )}
              {state.status === 'deciding' && <div>Deciding…</div>}
              {state.status === 'done' && (
                <div>
                  <strong>{state.outcome === 'approve' ? 'Delivered' : 'Withheld'}</strong>
                  {state.message && <div style={{ fontSize: '0.85rem' }}>{state.message}</div>}
                </div>
              )}
              {state.status === 'error' && <div style={{ color: 'crimson' }}>{state.error}</div>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

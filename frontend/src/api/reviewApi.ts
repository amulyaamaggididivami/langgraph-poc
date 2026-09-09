import type { Message } from '@ag-ui/client'

import { API_URL, ENDPOINTS } from '../constants'

export interface PendingReview {
  thread_id: string
  question_text: string
  updated_at: string
}

/** Loosely-typed ag-ui-protocol BaseEvent — this client only reads
 * `delta` off TEXT_MESSAGE_CONTENT frames and `messages` off the one
 * MESSAGES_SNAPSHOT frame each run ends with (the full, ordered
 * question+answer history for that thread — the same shape @ag-ui/client's
 * HttpAgent exposes as `.messages`, so a resumed thread's snapshot can
 * replace the Chat pane's message list directly). */
export interface AguiEvent {
  type: string
  delta?: string
  messages?: Message[]
  [key: string]: unknown
}

interface ApiError {
  code: string
  message: string
  retryable: boolean
  user_facing_copy_key: string
}

/** The subset of the real review API this page uses — lets tests pass a
 * fake instead of real fetch calls (same pattern as chatApi.ts's
 * ChatAgent). */
export interface ReviewApi {
  listPending(): Promise<PendingReview[]>
  decide(threadId: string, decision: 'approve' | 'reject', onEvent?: (event: AguiEvent) => void): Promise<void>
}

async function readErrorBody(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as ApiError
    return body.message ?? `request failed: ${res.status}`
  } catch {
    return `request failed: ${res.status}`
  }
}

async function listPending(): Promise<PendingReview[]> {
  const res = await fetch(`${API_URL}${ENDPOINTS.review}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  if (!res.ok) throw new Error(await readErrorBody(res))
  return (await res.json()) as PendingReview[]
}

/** Backend response is a POST /review/{thread_id}/decision SSE stream
 * (trd.md §API Contracts) — same wire shape as /chat, but this route
 * doesn't fit @ag-ui/client's HttpAgent (it always POSTs a
 * RunAgentInput body; this endpoint's body is just `{decision}`), so
 * this reads the stream directly. */
async function decide(
  threadId: string,
  decision: 'approve' | 'reject',
  onEvent?: (event: AguiEvent) => void,
): Promise<void> {
  const res = await fetch(`${API_URL}${ENDPOINTS.review}/${threadId}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  })
  if (!res.ok) throw new Error(await readErrorBody(res))
  if (!res.body) return

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''
    for (const chunk of chunks) {
      const trimmed = chunk.trim()
      if (!trimmed.startsWith('data:')) continue
      const jsonText = trimmed.slice(5).trim()
      if (!jsonText) continue
      try {
        onEvent?.(JSON.parse(jsonText) as AguiEvent)
      } catch {
        // malformed chunk — skip rather than fail the whole stream
      }
    }
  }
}

export const reviewApi: ReviewApi = { listPending, decide }

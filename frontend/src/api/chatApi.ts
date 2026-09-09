import { HttpAgent } from '@ag-ui/client'

import { API_URL, ENDPOINTS } from '../constants'

/** The subset of HttpAgent's API ChatForm actually uses — lets tests pass
 * a fake instead of a real HttpAgent (same dependency-injection pattern
 * the backend nodes use for their LLM clients). `threadId` is included
 * so the page holding both ChatForm and ReviewPage can tell whether a
 * review decision belongs to the thread currently open in Chat.
 * `setMessages` is included so that same page can also write a review
 * decision's resumed history back into the agent's own `messages` —
 * without it, `agent.messages` only ever grows via `addMessage()` and
 * never learns about an answer delivered out-of-band through Review,
 * so the next `addMessage()` call (the next question) builds on a copy
 * of history that's missing whatever Review just resolved. */
export type ChatAgent = Pick<HttpAgent, 'addMessage' | 'runAgent' | 'messages' | 'threadId' | 'setMessages'>

export function createChatAgent(threadId: string): ChatAgent {
  return new HttpAgent({
    url: `${API_URL}${ENDPOINTS.chat}`,
    threadId,
  })
}

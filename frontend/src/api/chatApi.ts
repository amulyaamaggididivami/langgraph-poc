import { HttpAgent } from '@ag-ui/client'

import { API_URL, ENDPOINTS } from '../constants'

/** The subset of HttpAgent's API ChatForm actually uses — lets tests pass
 * a fake instead of a real HttpAgent (same dependency-injection pattern
 * the backend nodes use for their LLM clients). */
export type ChatAgent = Pick<HttpAgent, 'addMessage' | 'runAgent' | 'messages'>

export function createChatAgent(threadId: string): ChatAgent {
  return new HttpAgent({
    url: `${API_URL}${ENDPOINTS.chat}`,
    threadId,
  })
}

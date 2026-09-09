import { HttpAgent } from '@ag-ui/client'

import { API_URL, ENDPOINTS } from '../constants'

/** The subset of HttpAgent's API ChatForm actually uses — lets tests pass
 * a fake instead of a real HttpAgent (same dependency-injection pattern
 * the backend nodes use for their LLM clients). `threadId` is included
 * so the page holding both ChatForm and ReviewPage can tell whether a
 * review decision belongs to the thread currently open in Chat. */
export type ChatAgent = Pick<HttpAgent, 'addMessage' | 'runAgent' | 'messages' | 'threadId'>

export function createChatAgent(threadId: string): ChatAgent {
  return new HttpAgent({
    url: `${API_URL}${ENDPOINTS.chat}`,
    threadId,
  })
}

import { API_URL, ENDPOINTS } from '../constants'

export interface ChatResponse {
  reply: string
}

export async function sendMessage(message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}${ENDPOINTS.chat}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })

  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`)
  }

  return res.json()
}

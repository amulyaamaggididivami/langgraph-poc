export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const ENDPOINTS = {
  chat: '/chat',
  review: '/review',
} as const

// The 4 questions app/constants/query_tool.py's PREDEFINED_QUERIES
// actually matches (exact text, no normalization) — kept in sync by
// hand since frontend/backend don't share a module. Buttons fill the
// input with this exact text so a query_tool match is guaranteed.
export const PREDEFINED_QUESTIONS = [
  'What is the cancellation rate?',
  'What is the total revenue?',
  'What is 18% of 1,240?',
  'Which clinic generated the most revenue?',
] as const

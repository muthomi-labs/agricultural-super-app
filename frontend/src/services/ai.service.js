import { env } from '@/config/env'
import { getAccessToken, httpClient } from '@/lib/http'
import { normalizeAIConversation, normalizeAIMessage } from '@/lib/normalize'

/**
 * AI Farming Assistant. The backend proxies to the model provider server-
 * side (see backend/app/services/ai_service.py) -- no provider API key
 * ever reaches the browser. Conversations and messages are persisted on
 * the backend (backend/app/models/ai_conversation.py, ai_message.py), so
 * history survives a page reload -- the frontend never holds the source
 * of truth, only a cached copy of what the API returned.
 */
export const aiService = {
  /**
   * Stateless one-shot completion (POST /ai/assistant) -- no conversation
   * is created or persisted. Used for the "Translate to Kiswahili" action
   * on an existing AI reply (see AiConversationPage.jsx): reuses this
   * same endpoint/service the chat itself calls, rather than a separate
   * translation system, per a single crafted user-turn prompt.
   */
  async askAssistant(messages) {
    const result = await httpClient.post('/ai/assistant', { messages })
    return result.reply
  },

  async listConversations() {
    const conversations = await httpClient.get('/ai/conversations')
    return conversations.map(normalizeAIConversation)
  },

  async createConversation(title) {
    const conversation = await httpClient.post('/ai/conversations', title ? { title } : {})
    return normalizeAIConversation(conversation)
  },

  async getConversation(id) {
    const conversation = await httpClient.get(`/ai/conversations/${id}`)
    return normalizeAIConversation(conversation)
  },

  async deleteConversation(id) {
    await httpClient.delete(`/ai/conversations/${id}`)
  },

  /** Non-streaming: waits for the complete reply. See streamMessage() for the incremental version. */
  async sendMessage(conversationId, content) {
    const result = await httpClient.post(`/ai/conversations/${conversationId}/messages`, { content })
    return {
      userMessage: normalizeAIMessage(result.user_message),
      assistantMessage: normalizeAIMessage(result.assistant_message),
    }
  },

  /**
   * Streams an assistant reply via Server-Sent Events
   * (POST /ai/conversations/:id/messages?stream=true -- see
   * backend/app/routes/ai_routes.py's _stream_conversation_message).
   *
   * httpClient can't be reused here -- it always awaits and JSON-parses
   * the full response body -- so this calls fetch() directly, attaching
   * the same bearer token httpClient does. `handlers` are invoked as
   * each SSE event arrives; the returned promise resolves once the
   * stream ends (successfully or with an in-band "error" event -- both
   * are reported through `handlers`, not by throwing, since by the time
   * either can happen the HTTP response is already a committed 200).
   *
   * `signal` (an AbortSignal, optional) lets the caller cancel -- see
   * store/slices/aiSlice.js's cancelAIStream(). This stops us from
   * waiting for or rendering any more of the reply and frees the UI to
   * send a new message immediately; it does NOT reach into the backend
   * and stop the AI provider's generation in progress there, which
   * keeps running to completion server-side regardless (gunicorn's sync
   * worker has no way to interrupt the blocking read mid-generation --
   * genuinely cancelling that would need a different worker/concurrency
   * model, out of scope for this pass). "Cancel" here means "stop
   * waiting for it," not "stop it happening."
   */
  async streamMessage(conversationId, content, handlers = {}, { signal } = {}) {
    const token = getAccessToken()
    const response = await fetch(`${env.apiBaseUrl}/ai/conversations/${conversationId}/messages?stream=true`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
      signal,
    })

    if (!response.ok || !response.body) {
      let message = response.statusText
      try {
        const body = await response.json()
        message = body.error ?? message
      } catch {
        // Non-JSON error body; keep the status-based message.
      }
      throw { status: response.status, message }
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const rawEvent = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        boundary = buffer.indexOf('\n\n')

        let eventName = 'message'
        let data = null
        for (const line of rawEvent.split('\n')) {
          if (line.startsWith('event:')) eventName = line.slice('event:'.length).trim()
          else if (line.startsWith('data:')) data = JSON.parse(line.slice('data:'.length).trim())
        }

        if (eventName === 'user_message') handlers.onUserMessage?.(normalizeAIMessage(data))
        else if (eventName === 'chunk') handlers.onChunk?.(data)
        else if (eventName === 'done') handlers.onDone?.()
        else if (eventName === 'error') handlers.onError?.(data)
      }
    }
  },
}

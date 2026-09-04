import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { aiService } from '@/services'

const initialState = {
  conversations: [],
  conversationsStatus: 'idle',
  conversationsError: null,
  current: null,
  currentStatus: 'idle',
  currentError: null,
  sending: false,
  sendError: null,
  // Text accumulated so far for an assistant reply that's still
  // streaming in; null when nothing is in flight. Kept separate from
  // `current.messages` until the stream finishes so a page reload (or
  // switching conversations) never has to reconcile a half-written
  // message against what the database actually persisted.
  streamingReply: null,
}

export const fetchAIConversations = createAsyncThunk(
  'ai/fetchConversations',
  async (_, { rejectWithValue }) => {
    try {
      return await aiService.listConversations()
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to load conversations.')
    }
  },
)

export const fetchAIConversation = createAsyncThunk(
  'ai/fetchConversation',
  async (conversationId, { rejectWithValue }) => {
    try {
      return await aiService.getConversation(conversationId)
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to load conversation.')
    }
  },
)

export const createAIConversation = createAsyncThunk(
  'ai/createConversation',
  async (title, { rejectWithValue }) => {
    try {
      return await aiService.createConversation(title)
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to start a new conversation.')
    }
  },
)

export const deleteAIConversation = createAsyncThunk(
  'ai/deleteConversation',
  async (conversationId, { rejectWithValue }) => {
    try {
      await aiService.deleteConversation(conversationId)
      return conversationId
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to delete conversation.')
    }
  },
)

// Tracks the in-flight stream's AbortController so cancelAIStream() (called
// from wherever the "Cancel" button lives) can reach it. Module-level, not
// Redux state, since an AbortController isn't serializable -- and a plain
// single slot is enough because the UI already only allows one send at a
// time (see the `sending` guard in AiConversationPage.jsx/FloatingAssistant.jsx).
let currentStreamController = null

/** Cancels the in-flight streamAIMessage(), if any. See streamMessage()'s
 * `signal` doc comment in ai.service.js for exactly what "cancel" means
 * here. A no-op if nothing is streaming. */
export function cancelAIStream() {
  currentStreamController?.abort()
}

/**
 * Sends a message and streams the reply. Not a plain createAsyncThunk --
 * it needs to dispatch several times as the stream progresses (the user
 * message landing, each text chunk, then completion/failure), not just
 * once when a promise resolves.
 */
export function streamAIMessage({ conversationId, content }) {
  return async (dispatch) => {
    dispatch(aiStreamStarted())
    const controller = new AbortController()
    currentStreamController = controller
    try {
      await aiService.streamMessage(
        conversationId,
        content,
        {
          onUserMessage: (message) => dispatch(aiUserMessageReceived({ conversationId, message })),
          onChunk: (text) => dispatch(aiChunkReceived(text)),
          onDone: () => dispatch(aiStreamCompleted({ conversationId })),
          onError: (message) =>
            dispatch(aiStreamFailed(message || 'The AI assistant could not respond. Please try again.')),
        },
        { signal: controller.signal },
      )
    } catch (error) {
      if (error?.name === 'AbortError') {
        dispatch(aiStreamCancelled())
      } else {
        dispatch(aiStreamFailed(error?.message ?? 'Failed to reach the AI assistant.'))
      }
    } finally {
      if (currentStreamController === controller) currentStreamController = null
    }
  }
}

function touchConversation(state, conversationId, updatedAt) {
  const conversation = state.conversations.find((c) => c.id === conversationId)
  if (conversation) {
    conversation.updatedAt = updatedAt
    state.conversations.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  }
}

const aiSlice = createSlice({
  name: 'ai',
  initialState,
  reducers: {
    aiStreamStarted(state) {
      state.sending = true
      state.sendError = null
      state.streamingReply = { content: '' }
    },
    aiUserMessageReceived(state, action) {
      const { conversationId, message } = action.payload
      if (state.current?.id === conversationId) {
        state.current.messages.push(message)
        if (state.current.title === null) {
          // Mirrors the backend auto-titling in ai_service._derive_title --
          // an approximation (no truncation) good enough until the next
          // fetch brings the server-computed title.
          state.current.title = message.content
        }
      }
      touchConversation(state, conversationId, message.createdAt)
    },
    aiChunkReceived(state, action) {
      if (state.streamingReply) {
        state.streamingReply.content += action.payload
      }
    },
    aiStreamCompleted(state, action) {
      const { conversationId } = action.payload
      const finalContent = state.streamingReply?.content ?? ''
      if (state.current?.id === conversationId) {
        const now = new Date().toISOString()
        state.current.messages.push({
          id: `local-${now}`,
          conversationId,
          role: 'assistant',
          content: finalContent,
          createdAt: now,
        })
        touchConversation(state, conversationId, now)
      }
      state.sending = false
      state.streamingReply = null
    },
    aiStreamFailed(state, action) {
      state.sending = false
      state.streamingReply = null
      state.sendError = action.payload
    },
    aiStreamCancelled(state) {
      // Deliberately not treated as an error (no sendError) and the
      // partial reply is dropped rather than kept as a message -- the
      // backend never persisted it (its own DB write only happens after
      // the generator finishes normally; see stream_message() in
      // ai_service.py), so keeping it locally would show the user
      // something a page reload would then make disappear.
      state.sending = false
      state.streamingReply = null
    },
    clearAISendError(state) {
      state.sendError = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAIConversations.pending, (state) => {
        state.conversationsStatus = 'loading'
        state.conversationsError = null
      })
      .addCase(fetchAIConversations.fulfilled, (state, action) => {
        state.conversations = action.payload
        state.conversationsStatus = 'ready'
      })
      .addCase(fetchAIConversations.rejected, (state, action) => {
        state.conversationsStatus = 'error'
        state.conversationsError = action.payload
      })
      .addCase(fetchAIConversation.pending, (state) => {
        state.currentStatus = 'loading'
        state.currentError = null
      })
      .addCase(fetchAIConversation.fulfilled, (state, action) => {
        state.current = action.payload
        state.currentStatus = 'ready'
      })
      .addCase(fetchAIConversation.rejected, (state, action) => {
        state.currentStatus = 'error'
        state.currentError = action.payload
      })
      .addCase(createAIConversation.fulfilled, (state, action) => {
        state.conversations.unshift(action.payload)
        state.current = action.payload
        state.currentStatus = 'ready'
      })
      .addCase(deleteAIConversation.fulfilled, (state, action) => {
        const conversationId = action.payload
        state.conversations = state.conversations.filter((c) => c.id !== conversationId)
        if (state.current?.id === conversationId) {
          state.current = null
          state.currentStatus = 'idle'
        }
      })
  },
})

export const {
  aiStreamStarted,
  aiUserMessageReceived,
  aiChunkReceived,
  aiStreamCompleted,
  aiStreamFailed,
  aiStreamCancelled,
  clearAISendError,
} = aiSlice.actions

export default aiSlice.reducer

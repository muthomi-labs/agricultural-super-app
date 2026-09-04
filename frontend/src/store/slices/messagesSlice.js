import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { messagesService } from '@/services'

const initialState = {
  conversations: [],
  conversationsStatus: 'idle',
  conversationsError: null,
  current: null,
  currentStatus: 'idle',
  currentError: null,
  sending: false,
  sendError: null,
}

export const fetchConversations = createAsyncThunk(
  'messages/fetchConversations',
  async (_, { rejectWithValue }) => {
    try {
      return await messagesService.listConversations()
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to load conversations.')
    }
  },
)

export const fetchConversation = createAsyncThunk(
  'messages/fetchConversation',
  async (conversationId, { rejectWithValue }) => {
    try {
      return await messagesService.getConversation(conversationId)
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to load conversation.')
    }
  },
)

/**
 * Starts (or reuses) a direct conversation with another user. The backend
 * always creates a new conversation on POST /conversations -- it doesn't
 * dedupe -- so an existing 1:1 conversation with that user is looked for
 * client-side first, to avoid spawning a fresh empty thread every time
 * "Message" is clicked on the same person.
 */
export const startConversationWithUser = createAsyncThunk(
  'messages/startConversationWithUser',
  async (otherUserId, { getState, rejectWithValue }) => {
    try {
      const myId = getState().auth.user?.user.id
      let conversations = getState().messages.conversations
      if (conversations.length === 0) {
        conversations = await messagesService.listConversations()
      }

      const existing = conversations.find((c) => {
        const ids = c.participants.map((p) => p.userId)
        return ids.length === 2 && ids.includes(myId) && ids.includes(otherUserId)
      })
      if (existing) return existing

      return await messagesService.startConversation([otherUserId])
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to start conversation.')
    }
  },
)

export const sendMessage = createAsyncThunk(
  'messages/sendMessage',
  async ({ conversationId, content }, { rejectWithValue }) => {
    try {
      const message = await messagesService.sendMessage(conversationId, content)
      return { conversationId, message }
    } catch (error) {
      return rejectWithValue(error?.message ?? 'Failed to send message.')
    }
  },
)

export const markMessageRead = createAsyncThunk(
  'messages/markMessageRead',
  async (messageId, { rejectWithValue }) => {
    try {
      return await messagesService.markRead(messageId)
    } catch {
      // Best-effort -- a failed read receipt shouldn't surface as a
      // user-facing error, the conversation is still fully usable.
      return rejectWithValue(null)
    }
  },
)

const messagesSlice = createSlice({
  name: 'messages',
  initialState,
  reducers: {
    clearSendError(state) {
      state.sendError = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConversations.pending, (state) => {
        state.conversationsStatus = 'loading'
        state.conversationsError = null
      })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.conversations = action.payload
        state.conversationsStatus = 'ready'
      })
      .addCase(fetchConversations.rejected, (state, action) => {
        state.conversationsStatus = 'error'
        state.conversationsError = action.payload
      })
      .addCase(fetchConversation.pending, (state) => {
        state.currentStatus = 'loading'
        state.currentError = null
      })
      .addCase(fetchConversation.fulfilled, (state, action) => {
        state.current = action.payload
        state.currentStatus = 'ready'
      })
      .addCase(fetchConversation.rejected, (state, action) => {
        state.currentStatus = 'error'
        state.currentError = action.payload
      })
      .addCase(startConversationWithUser.fulfilled, (state, action) => {
        state.current = action.payload
        state.currentStatus = 'ready'
        if (!state.conversations.some((c) => c.id === action.payload.id)) {
          state.conversations.unshift(action.payload)
        }
      })
      .addCase(sendMessage.pending, (state) => {
        state.sending = true
        state.sendError = null
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.sending = false
        if (state.current?.id === action.payload.conversationId) {
          state.current.messages.push(action.payload.message)
        }
        const conversation = state.conversations.find((c) => c.id === action.payload.conversationId)
        if (conversation) {
          conversation.updatedAt = action.payload.message.createdAt
          state.conversations.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.sending = false
        state.sendError = action.payload
      })
      .addCase(markMessageRead.fulfilled, (state, action) => {
        if (state.current) {
          const message = state.current.messages.find((m) => m.id === action.payload.id)
          if (message) message.isRead = true
        }
      })
  },
})

export const { clearSendError } = messagesSlice.actions

export default messagesSlice.reducer

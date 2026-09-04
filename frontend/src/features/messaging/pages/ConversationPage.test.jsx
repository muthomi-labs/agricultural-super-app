import { configureStore } from '@reduxjs/toolkit'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import authReducer from '@/store/slices/authSlice'
import messagesReducer from '@/store/slices/messagesSlice'
import { ConversationPage } from './ConversationPage'

vi.mock('@/services', () => ({
  messagesService: {
    getConversation: vi.fn().mockResolvedValue({
      id: 5,
      participants: [
        { userId: 1, participant: { user: { id: 1, username: 'amina' }, profile: { firstName: 'Amina', lastName: 'W' } } },
        { userId: 2, participant: { user: { id: 2, username: 'brian' }, profile: { firstName: 'Brian', lastName: 'K' } } },
      ],
      messages: [],
    }),
    markRead: vi.fn(),
    sendMessage: vi.fn(),
  },
}))

function renderConversationPage() {
  const store = configureStore({
    reducer: { auth: authReducer, messages: messagesReducer },
    preloadedState: {
      auth: {
        status: 'authenticated',
        user: { user: { id: 1, username: 'amina', role: 'farmer' }, profile: { firstName: 'Amina', lastName: 'W' } },
      },
    },
  })
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/messages/5']}>
        <Routes>
          <Route path="/messages/:conversationId" element={<ConversationPage />} />
        </Routes>
      </MemoryRouter>
    </Provider>,
  )
}

describe('ConversationPage typing', () => {
  it('keeps the message composer focused while typing continuously', async () => {
    const user = userEvent.setup()
    renderConversationPage()

    const textarea = await screen.findByRole('textbox', { name: /message/i })
    const message = 'Are you free to discuss the maize order tomorrow morning?'
    await user.click(textarea)
    await user.type(textarea, message)

    expect(textarea).toHaveValue(message)
    expect(textarea).toHaveFocus()
  })
})

describe('ConversationPage send failure', () => {
  it('keeps the draft and shows an error when sending fails, instead of silently losing it', async () => {
    const { messagesService } = await import('@/services')
    messagesService.sendMessage.mockRejectedValueOnce({ message: 'Network error' })

    const user = userEvent.setup()
    renderConversationPage()

    const textarea = await screen.findByRole('textbox', { name: /message/i })
    const message = 'Are you free to discuss the maize order tomorrow morning?'
    await user.click(textarea)
    await user.type(textarea, message)
    await user.click(screen.getByRole('button', { name: /send message/i }))

    expect(await screen.findByText(/could not send your message/i)).toBeInTheDocument()
    expect(textarea).toHaveValue(message)
  })

  it('clears the draft after a successful send', async () => {
    const { messagesService } = await import('@/services')
    messagesService.sendMessage.mockResolvedValueOnce({
      id: 99,
      conversationId: 5,
      senderId: 1,
      content: 'Are you free tomorrow?',
      createdAt: '2026-09-04T10:00:00Z',
      isRead: false,
    })

    const user = userEvent.setup()
    renderConversationPage()

    const textarea = await screen.findByRole('textbox', { name: /message/i })
    await user.click(textarea)
    await user.type(textarea, 'Are you free tomorrow?')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    expect(await screen.findByText('Are you free tomorrow?')).toBeInTheDocument()
    expect(textarea).toHaveValue('')
  })
})

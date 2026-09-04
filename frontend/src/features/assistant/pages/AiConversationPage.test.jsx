import { configureStore } from '@reduxjs/toolkit'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import aiReducer from '@/store/slices/aiSlice'
import { AiConversationPage } from './AiConversationPage'

const { conversation } = vi.hoisted(() => ({
  conversation: {
    id: 7,
    title: 'Watering tomatoes',
    createdAt: '2026-09-04T10:00:00Z',
    updatedAt: '2026-09-04T10:00:00Z',
    messages: [
      { id: 1, conversationId: 7, role: 'user', content: 'How often should I water tomatoes?', createdAt: '2026-09-04T10:00:00Z' },
      { id: 2, conversationId: 7, role: 'assistant', content: 'Once a week, more in sandy soil.', createdAt: '2026-09-04T10:00:05Z' },
    ],
  },
}))

vi.mock('@/services', () => ({
  aiService: {
    getConversation: vi.fn().mockResolvedValue(conversation),
    streamMessage: vi.fn().mockResolvedValue(undefined),
    askAssistant: vi.fn(),
  },
}))

function renderPage() {
  const store = configureStore({ reducer: { ai: aiReducer } })
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/assistant/7']}>
        <Routes>
          <Route path="/assistant/:conversationId" element={<AiConversationPage />} />
        </Routes>
      </MemoryRouter>
    </Provider>,
  )
}

describe('AiConversationPage "Explain more"', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows "Explain more" only on the most recent assistant reply', async () => {
    renderPage()
    const buttons = await screen.findAllByRole('button', { name: /explain more/i })
    // Only the last (and here, only) assistant message gets the action.
    expect(buttons).toHaveLength(1)
  })

  it('sends the explain-more prompt as a normal follow-up message', async () => {
    const { aiService } = await import('@/services')
    const user = userEvent.setup()
    renderPage()

    const button = await screen.findByRole('button', { name: /explain more/i })
    await user.click(button)

    expect(aiService.streamMessage).toHaveBeenCalledWith(
      7,
      'Can you explain that in more detail?',
      expect.any(Object),
      expect.any(Object),
    )
  })
})

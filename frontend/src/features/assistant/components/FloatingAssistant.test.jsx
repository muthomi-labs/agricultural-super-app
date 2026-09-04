import { configureStore } from '@reduxjs/toolkit'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import aiReducer from '@/store/slices/aiSlice'
import { FloatingAssistant } from './FloatingAssistant'

vi.mock('@/services', () => ({
  aiService: {
    listConversations: vi.fn().mockResolvedValue([]),
    createConversation: vi.fn(),
    getConversation: vi.fn(),
    deleteConversation: vi.fn(),
    sendMessage: vi.fn(),
    streamMessage: vi.fn(),
  },
}))

function renderAssistant(initialPath = '/') {
  const store = configureStore({ reducer: { ai: aiReducer } })
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[initialPath]}>
        <FloatingAssistant />
      </MemoryRouter>
    </Provider>,
  )
}

describe('FloatingAssistant', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders collapsed by default without covering the page', () => {
    renderAssistant()
    expect(screen.getByRole('button', { name: /open ai assistant/i })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('expands into a panel when the trigger is clicked, and closes again', async () => {
    const user = userEvent.setup()
    renderAssistant()

    await user.click(screen.getByRole('button', { name: /open ai assistant/i }))
    expect(screen.getByRole('dialog', { name: /agricultural ai assistant/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /new conversation/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /close ai assistant/i }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /open ai assistant/i })).toBeInTheDocument()
  })

  it('does not render on the full assistant page, to avoid a redundant duplicate UI', () => {
    renderAssistant('/assistant')
    expect(screen.queryByRole('button', { name: /open ai assistant/i })).not.toBeInTheDocument()
  })

  it('keeps the chat composer focused while typing continuously', async () => {
    const { aiService } = await import('@/services')
    aiService.createConversation.mockResolvedValue({ id: 1, title: null, messages: [] })

    const user = userEvent.setup()
    renderAssistant()

    await user.click(screen.getByRole('button', { name: /open ai assistant/i }))
    await user.click(screen.getByRole('button', { name: /new conversation/i }))

    const textarea = await screen.findByLabelText(/ask the assistant/i)
    const question = 'What fertilizer should I use for maize this season?'
    await user.click(textarea)
    await user.type(textarea, question)

    expect(textarea).toHaveValue(question)
    expect(textarea).toHaveFocus()
  })

  it('cancels an in-flight stream and unlocks the composer again', async () => {
    const { aiService } = await import('@/services')
    aiService.createConversation.mockResolvedValue({ id: 1, title: null, messages: [] })
    // Mirrors what a real aborted fetch() does (see ai.service.js's
    // streamMessage signal doc comment): the promise only settles when
    // the signal fires, rejecting with an AbortError.
    aiService.streamMessage.mockImplementation(
      (_conversationId, _content, _handlers, { signal } = {}) =>
        new Promise((_resolve, reject) => {
          signal?.addEventListener('abort', () => {
            const error = new Error('The operation was aborted.')
            error.name = 'AbortError'
            reject(error)
          })
        }),
    )

    const user = userEvent.setup()
    renderAssistant()

    await user.click(screen.getByRole('button', { name: /open ai assistant/i }))
    await user.click(screen.getByRole('button', { name: /new conversation/i }))

    const textarea = await screen.findByLabelText(/ask the assistant/i)
    await user.type(textarea, 'How often should I water tomatoes?')
    await user.click(screen.getByRole('button', { name: /^send$/i }))

    const cancelButton = await screen.findByRole('button', { name: /cancel/i })
    expect(screen.queryByRole('button', { name: /^send$/i })).not.toBeInTheDocument()

    await user.click(cancelButton)

    expect(await screen.findByRole('button', { name: /^send$/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument()
  })
})

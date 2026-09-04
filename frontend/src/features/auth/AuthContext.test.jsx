import { configureStore } from '@reduxjs/toolkit'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { afterEach, describe, expect, it, vi } from 'vitest'
import authReducer from '@/store/slices/authSlice'
import { LanguageSwitcher } from '@/components/ui'
import i18n, { LANGUAGE_STORAGE_KEY } from '@/i18n'

vi.mock('@/services', () => ({
  usersService: { updateLanguage: vi.fn() },
}))

function renderSwitcherAsUser(language = 'en') {
  const store = configureStore({
    reducer: { auth: authReducer },
    preloadedState: {
      auth: {
        status: 'authenticated',
        user: { user: { id: 1, username: 'amina', role: 'farmer', language }, profile: {} },
      },
    },
  })
  return render(
    <Provider store={store}>
      <LanguageSwitcher />
    </Provider>,
  )
}

describe('AuthContext.changeLanguage', () => {
  afterEach(() => {
    i18n.changeLanguage('en')
    window.localStorage.removeItem(LANGUAGE_STORAGE_KEY)
    vi.clearAllMocks()
  })

  it('persists the new language to the signed-in user\'s account, not just localStorage', async () => {
    const { usersService } = await import('@/services')
    usersService.updateLanguage.mockResolvedValue({
      user: { id: 1, username: 'amina', role: 'farmer', language: 'sw' },
      profile: {},
    })

    const user = userEvent.setup()
    renderSwitcherAsUser('en')

    await user.click(screen.getByRole('button', { name: 'Kiswahili' }))

    expect(usersService.updateLanguage).toHaveBeenCalledWith('sw')
  })

  it('switches the UI language immediately, without waiting on the server round-trip', async () => {
    const { usersService } = await import('@/services')
    // Never resolves within the test -- the UI should still flip instantly.
    usersService.updateLanguage.mockReturnValue(new Promise(() => {}))

    const user = userEvent.setup()
    renderSwitcherAsUser('en')

    await user.click(screen.getByRole('button', { name: 'Kiswahili' }))

    expect(i18n.language).toBe('sw')
  })
})

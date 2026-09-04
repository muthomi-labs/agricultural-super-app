import { configureStore } from '@reduxjs/toolkit'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import authReducer from '@/store/slices/authSlice'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { LanguageSwitcher } from '@/components/ui'
import i18n, { LANGUAGE_STORAGE_KEY, SUPPORTED_LANGUAGES } from '@/i18n'

function renderWithProviders(ui) {
  const store = configureStore({
    reducer: { auth: authReducer },
    preloadedState: { auth: { status: 'unauthenticated', user: null } },
  })
  return render(
    <Provider store={store}>
      <MemoryRouter>{ui}</MemoryRouter>
    </Provider>,
  )
}

describe('i18n setup', () => {
  afterEach(() => {
    // Every other test file assumes English -- never leak a language
    // change across files sharing this same singleton instance.
    i18n.changeLanguage('en')
    window.localStorage.removeItem(LANGUAGE_STORAGE_KEY)
  })

  it('supports exactly English and Kiswahili', () => {
    expect(SUPPORTED_LANGUAGES).toEqual(['en', 'sw'])
  })

  it('renders the login page in English by default', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log in' })).toBeInTheDocument()
  })

  it('renders the login page in Kiswahili once the language is switched', async () => {
    await i18n.changeLanguage('sw')
    renderWithProviders(<LoginPage />)
    expect(screen.getByRole('heading', { name: 'Karibu tena' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ingia' })).toBeInTheDocument()
  })

  it('translates agricultural terminology using the app\'s own glossary, not a generic guess', async () => {
    await i18n.changeLanguage('sw')
    expect(i18n.t('common:roles.farmer')).toBe('Mkulima')
    expect(i18n.t('common:roles.expert')).toBe('Mtaalamu')
  })

  it('does not translate the app name, a proper noun', () => {
    expect(i18n.t('common:appName')).toBe('AgriConnect')
    i18n.changeLanguage('sw')
    expect(i18n.t('common:appName')).toBe('AgriConnect')
  })
})

describe('LanguageSwitcher', () => {
  afterEach(() => {
    i18n.changeLanguage('en')
    window.localStorage.removeItem(LANGUAGE_STORAGE_KEY)
  })

  it('shows both English and Kiswahili options, with the active one marked', () => {
    renderWithProviders(<LanguageSwitcher />)
    const english = screen.getByRole('button', { name: 'English' })
    const kiswahili = screen.getByRole('button', { name: 'Kiswahili' })
    expect(english).toHaveAttribute('aria-pressed', 'true')
    expect(kiswahili).toHaveAttribute('aria-pressed', 'false')
  })

  it('switches the active language when Kiswahili is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<LanguageSwitcher />)

    await user.click(screen.getByRole('button', { name: 'Kiswahili' }))

    expect(i18n.language).toBe('sw')
    expect(screen.getByRole('button', { name: 'Kiswahili' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('persists the chosen language to localStorage so it survives a refresh', async () => {
    const user = userEvent.setup()
    renderWithProviders(<LanguageSwitcher />)

    await user.click(screen.getByRole('button', { name: 'Kiswahili' }))

    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('sw')
  })
})

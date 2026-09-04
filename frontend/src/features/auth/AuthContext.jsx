import { useCallback, useEffect } from 'react'
import i18n from '@/i18n'
import { usersService } from '@/services'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { UNAUTHORIZED_EVENT } from '@/lib/http'
import {
  changePassword as changePasswordThunk,
  forgotPassword as forgotPasswordThunk,
  initializeSession,
  login as loginThunk,
  logout as logoutThunk,
  profileUpdated,
  register as registerThunk,
  resetPassword as resetPasswordThunk,
} from '@/store/slices/authSlice'

/**
 * Authentication layer built on the Redux `auth` slice.
 *
 * Keeps the same public API the pages rely on:
 *   useAuth() -> { status, user, login, register, logout, refreshProfile }
 */

/**
 * Initializes the session on app mount (restores the stored token).
 * Renders children immediately; the `status` flag drives route guards.
 */
export function AuthProvider({ children }) {
  const dispatch = useAppDispatch()
  const user = useAppSelector((state) => state.auth.user)

  useEffect(() => {
    dispatch(initializeSession())
  }, [dispatch])

  useEffect(() => {
    function handleUnauthorized() {
      dispatch(logoutThunk())
    }
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
  }, [dispatch])

  // Once a session is known (login, register, or a restored session via
  // /auth/me), the account's own saved language preference becomes the
  // source of truth and overrides whatever a signed-out visitor had
  // picked with the language switcher (see LanguageSwitcher.jsx) --
  // "Default to English for existing users unless another preference
  // already exists" only makes sense read this way: the account, not
  // the browser, is what "already exists" refers to once you're logged
  // in. Logging out leaves i18next on whatever it was already showing
  // (typically that same account language) rather than snapping back to
  // a guest default, which would be a jarring, pointless flash.
  useEffect(() => {
    const preferred = user?.user?.language
    if (preferred && preferred !== i18n.language) {
      i18n.changeLanguage(preferred)
    }
  }, [user])

  return children
}

export function useAuth() {
  const dispatch = useAppDispatch()
  const status = useAppSelector((state) => state.auth.status)
  const user = useAppSelector((state) => state.auth.user)

  const login = useCallback(
    (usernameOrEmail, password) =>
      dispatch(loginThunk({ usernameOrEmail, password })).unwrap(),
    [dispatch],
  )

  const register = useCallback(
    (input) => dispatch(registerThunk(input)).unwrap(),
    [dispatch],
  )

  const logout = useCallback(() => {
    dispatch(logoutThunk())
  }, [dispatch])

  const refreshProfile = useCallback(
    (profile) => dispatch(profileUpdated(profile)),
    [dispatch],
  )

  const forgotPassword = useCallback(
    (email) => dispatch(forgotPasswordThunk(email)).unwrap(),
    [dispatch],
  )

  const resetPassword = useCallback(
    (token, password) => dispatch(resetPasswordThunk({ token, password })).unwrap(),
    [dispatch],
  )

  const changePassword = useCallback(
    (currentPassword, newPassword) =>
      dispatch(changePasswordThunk({ currentPassword, newPassword })).unwrap(),
    [dispatch],
  )

  /**
   * Switches the UI language immediately (so the change feels instant,
   * regardless of network speed), then -- only for a signed-in user --
   * persists it to their account (see PUT /users/me/language) so it
   * follows them to their next session/device. A signed-out visitor's
   * choice still survives a refresh via i18next-browser-languagedetector's
   * own localStorage caching (see src/i18n/index.js), just not across
   * devices until they log in.
   */
  const changeLanguage = useCallback(
    async (language) => {
      i18n.changeLanguage(language)
      if (!user) return
      try {
        const updated = await usersService.updateLanguage(language)
        dispatch(profileUpdated(updated))
      } catch {
        // Best-effort persistence -- the UI has already switched
        // language, and a transient save failure here shouldn't block
        // or roll that back; it just means the preference might not
        // follow the user to their next session.
      }
    },
    [dispatch, user],
  )

  return {
    status,
    user,
    login,
    register,
    logout,
    refreshProfile,
    forgotPassword,
    resetPassword,
    changePassword,
    changeLanguage,
  }
}

/** Normalize an unknown error into a human-readable message. */
export function errorMessage(error) {
  if (typeof error === 'string') return error
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return error.message
  }
  return 'Something went wrong. Please try again.'
}
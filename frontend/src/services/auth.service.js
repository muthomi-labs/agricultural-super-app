import { env } from '@/config/env'
import { httpClient, setAccessToken } from '@/lib/http'
import { toUserProfile } from '@/lib/normalize'
import { mockAuth, mockSession } from './mocks/mockApi'

/**
 * Authentication service.
 *
 * The backend accepts either `username` or `email` as the login
 * identifier under either key (it checks both) -- sending the same
 * value under both keys means the caller here never has to guess which
 * one the user typed (see backend/app/routes/auth_routes.py).
 */
export const authService = {
  async login(usernameOrEmail, password) {
    if (env.useMocks) return mockAuth.login(usernameOrEmail, password)

    const session = await httpClient.post('/auth/login', {
      username: usernameOrEmail,
      email: usernameOrEmail,
      password,
    })
    return { accessToken: session.token, user: toUserProfile(session.user) }
  },

  async register({ username, email, password, role, language, firstName, lastName }) {
    if (env.useMocks) return mockAuth.register({ username, email, password, language, firstName, lastName })

    const session = await httpClient.post('/auth/register', {
      username,
      email,
      password,
      role: role ?? 'farmer',
      language: language ?? 'en',
    })

    // The token must be stored before the profile call below, since
    // httpClient reads it from storage per-request.
    setAccessToken(session.token)

    let user = toUserProfile(session.user)
    if (firstName || lastName) {
      const profile = await httpClient.put('/users/me/profile', {
        first_name: firstName || undefined,
        last_name: lastName || undefined,
      })
      user = { ...user, profile: { ...user.profile, firstName: profile.first_name, lastName: profile.last_name } }
    }

    return { accessToken: session.token, user }
  },

  async me() {
    if (env.useMocks) return mockSession.me(1)
    const user = await httpClient.get('/auth/me')
    return toUserProfile(user)
  },

  async forgotPassword(email) {
    if (env.useMocks) return { message: 'If an account exists for that email, a reset link has been sent.' }
    return httpClient.post('/auth/forgot-password', { email })
  },

  async resetPassword(token, password) {
    if (env.useMocks) return { message: 'Password has been reset.' }
    return httpClient.post('/auth/reset-password', { token, password })
  },

  async changePassword(currentPassword, newPassword) {
    if (env.useMocks) return { message: 'Password changed.' }
    return httpClient.put('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
}

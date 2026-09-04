import { env } from '@/config/env'
import { httpClient } from '@/lib/http'
import { toUserProfile } from '@/lib/normalize'
import { mockUsers } from './mocks/mockApi'

export const usersService = {
  /** Persists the caller's UI/AI language preference server-side (see
   * app/routes/user_routes.py's PUT /users/me/language). `language` is
   * "en" or "sw". */
  async updateLanguage(language) {
    if (env.useMocks) return mockUsers.updateLanguage(language)
    const user = await httpClient.put('/users/me/language', { language })
    return toUserProfile(user)
  },

  async searchUsers(query, { page = 1, pageSize = 20 } = {}) {
    const term = query.trim()
    if (!term) return { items: [], page, pageSize }
    if (env.useMocks) return mockUsers.searchUsers(term, page, pageSize)
    const params = new URLSearchParams({ search: term, page, per_page: pageSize })
    const users = await httpClient.get(`/users?${params.toString()}`)
    return { items: users.map(toUserProfile), page, pageSize }
  },
}

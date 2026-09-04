import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { LoadingState } from '@/components/ui'
import { useAuth } from './AuthContext'

/**
 * Guards routes that require authentication. While the session is being
 * restored a loading state is shown; unauthenticated users are redirected
 * to the login page (remembering where they came from).
 */
export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()
  const { t } = useTranslation('common')

  if (status === 'loading') {
    return <LoadingState label={t('states.checkingSession')} />
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
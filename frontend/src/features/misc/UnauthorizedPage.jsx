import { useTranslation } from 'react-i18next'
import { EmptyState, Button } from '@/components/ui'

export function UnauthorizedPage() {
  const { t } = useTranslation('auth')
  return (
    <EmptyState
      icon="🚫"
      title={t('unauthorized.title')}
      description={t('unauthorized.description')}
      action={<Button to="/">{t('unauthorized.goHome')}</Button>}
    />
  )
}

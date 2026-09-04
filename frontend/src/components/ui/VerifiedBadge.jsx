import { useTranslation } from 'react-i18next'
import { Badge } from './Badge'

/** Shows the expert verification badge only when the profile is verified. */
export function VerifiedBadge({ profile }) {
  const { t } = useTranslation('common')
  if (!profile.isVerified) return null
  return <Badge variant="verified">✓ {t('verified')}</Badge>
}
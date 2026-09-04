import { useTranslation } from 'react-i18next'
import { Spinner } from './Spinner'
import './ui.css'

export function LoadingState({ label }) {
  const { t } = useTranslation('common')
  return (
    <div className="asa-state" role="status" aria-live="polite">
      <Spinner size="lg" />
      <p className="asa-state__description">{label ?? t('states.loading')}</p>
    </div>
  )
}
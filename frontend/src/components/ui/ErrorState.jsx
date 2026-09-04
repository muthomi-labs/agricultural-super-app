import { useTranslation } from 'react-i18next'
import { Button } from './Button'
import './ui.css'

export function ErrorState({ title, message, onRetry }) {
  const { t } = useTranslation('common')
  return (
    <div className="asa-state asa-state--error" role="alert">
      <span className="asa-state__icon" aria-hidden="true">
        ⚠️
      </span>
      <h3 className="asa-state__title">{title ?? t('states.somethingWrong')}</h3>
      <p className="asa-state__description">{message ?? t('states.couldNotLoad')}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          {t('buttons.tryAgain')}
        </Button>
      )}
    </div>
  )
}
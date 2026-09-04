import { useTranslation } from 'react-i18next'
import { CheckIcon, XIcon } from '@/components/icons'
import { evaluatePassword } from '@/lib/passwordPolicy'
import './ui.css'

/**
 * Live-updating password requirement checklist. `role="status"` +
 * `aria-live="polite"` so screen reader users hear updates as they type,
 * without being interrupted mid-keystroke (polite, not assertive).
 */
export function PasswordRequirements({ password }) {
  const { t } = useTranslation('auth')
  const requirements = evaluatePassword(password)

  return (
    <ul className="asa-password-requirements" role="status" aria-live="polite">
      {requirements.map((req) => (
        <li
          key={req.key}
          className={`asa-password-requirements__item ${req.met ? 'asa-password-requirements__item--met' : ''}`}
        >
          {req.met ? (
            <CheckIcon width={14} height={14} aria-hidden="true" />
          ) : (
            <XIcon width={14} height={14} aria-hidden="true" />
          )}
          <span>{t(`passwordRequirements.${req.key}`)}</span>
        </li>
      ))}
    </ul>
  )
}

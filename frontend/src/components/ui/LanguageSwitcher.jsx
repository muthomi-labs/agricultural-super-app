import { useTranslation } from 'react-i18next'
import { useAuth } from '@/features/auth/AuthContext'
import { SUPPORTED_LANGUAGES } from '@/i18n'
import './ui.css'

/**
 * English/Kiswahili toggle. Reads the active language from i18next
 * directly (rather than from the authenticated user, which is only
 * available once logged in) so it works identically on the pre-auth
 * login/register pages and everywhere inside the authenticated app --
 * see AuthContext.jsx's changeLanguage for what happens on selection
 * (instant UI switch, plus a best-effort server persist if signed in).
 */
export function LanguageSwitcher({ className = '' }) {
  const { t, i18n } = useTranslation('common')
  const { changeLanguage } = useAuth()
  const current = i18n.language?.startsWith('sw') ? 'sw' : 'en'

  return (
    <div
      className={`asa-lang-switcher ${className}`.trim()}
      role="group"
      aria-label={t('language.select')}
    >
      {SUPPORTED_LANGUAGES.map((lng) => (
        <button
          key={lng}
          type="button"
          className={`asa-lang-switcher__option ${
            current === lng ? 'asa-lang-switcher__option--active' : ''
          }`}
          aria-pressed={current === lng}
          onClick={() => changeLanguage(lng)}
        >
          {t(`language.${lng}`)}
        </button>
      ))}
    </div>
  )
}

import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CommunityIcon, LeafIcon, MessageIcon, UsersIcon } from '@/components/icons'
import { LanguageSwitcher } from '@/components/ui'
import './auth.css'

/**
 * Split-panel layout shared by every auth page (login, register,
 * forgot/reset password): a white form panel and a brand panel with an
 * original decorative composition -- soft blob shapes plus small
 * "feature chips" built from the app's own icon set (Community, Experts,
 * Messages), rather than a literal illustration. That's a deliberate
 * choice, not a shortcut: it ties the hero visual directly to what the
 * product actually does, and sidesteps any question of reproducing
 * someone else's illustrated artwork.
 *
 * The right panel collapses away below the tablet breakpoint (see
 * auth.css) -- the form itself never depends on it being visible.
 */
export function AuthLayout({ title, subtitle, children, footer }) {
  const { t } = useTranslation('auth')

  return (
    <div className="asa-auth">
      <div className="asa-auth__card">
        <div className="asa-auth__form-panel">
          <div className="asa-auth__top-row">
            <Link to="/" className="asa-auth__brand">
              <span className="asa-auth__brand-mark" aria-hidden="true">
                <LeafIcon width={18} height={18} />
              </span>
              Agri<span>Connect</span>
            </Link>
            <LanguageSwitcher />
          </div>

          <div className="asa-auth__form-body">
            <p className="asa-auth__eyebrow">{t('layout.welcome')}</p>
            <h1 className="asa-auth__title">{title}</h1>
            {subtitle && <p className="asa-auth__subtitle">{subtitle}</p>}
            {children}
          </div>

          <p className="asa-auth__footer">{footer}</p>
        </div>

        <aside className="asa-auth__brand-panel" aria-hidden="true">
          <div className="asa-auth__blob asa-auth__blob--1" />
          <div className="asa-auth__blob asa-auth__blob--2" />

          <div className="asa-auth__hero-badge">
            <LeafIcon width={40} height={40} />
          </div>

          <div className="asa-auth__chip asa-auth__chip--1">
            <UsersIcon width={16} height={16} />
            <span>{t('layout.chipExperts')}</span>
          </div>
          <div className="asa-auth__chip asa-auth__chip--2">
            <CommunityIcon width={16} height={16} />
            <span>{t('layout.chipCommunities')}</span>
          </div>
          <div className="asa-auth__chip asa-auth__chip--3">
            <MessageIcon width={16} height={16} />
            <span>{t('layout.chipMessaging')}</span>
          </div>

          <div className="asa-auth__hero-text">
            <h2>{t('layout.heroTitle')}</h2>
            <p>{t('layout.heroDescription')}</p>
          </div>
        </aside>
      </div>
    </div>
  )
}

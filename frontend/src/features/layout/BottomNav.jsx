import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/features/auth/AuthContext'
import { bottomNavItems } from './nav'
import { CreateButton } from './CreateButton'
import './layout.css'

export function BottomNav() {
  const { t } = useTranslation('nav')
  const { user } = useAuth()
  const isAdmin = user?.user.role === 'admin'
  const visibleItems = bottomNavItems.filter((item) => !item.adminOnly || isAdmin)

  return (
    <nav className="asa-bottom-nav" aria-label="Main">
      {visibleItems.map((item) =>
        item.to === '/create' ? (
          <span className="asa-bottom-nav__link asa-bottom-nav__link--create-slot" key={item.to}>
            <CreateButton variant="bottom-nav" />
          </span>
        ) : (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `asa-bottom-nav__link ${isActive ? 'asa-bottom-nav__link--active' : ''}`
            }
          >
            {item.icon}
            <span>{t(item.labelKey)}</span>
          </NavLink>
        ),
      )}
    </nav>
  )
}

import { useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Dropdown, LanguageSwitcher } from '@/components/ui'
import { HeartIcon, MessageIcon, SearchIcon } from '@/components/icons'
import { useAuth } from '@/features/auth/AuthContext'
import { fetchUnreadCount } from '@/store/slices/notificationsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import './layout.css'

export function Header() {
  const { t } = useTranslation(['nav', 'common'])
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const unreadCount = useAppSelector((state) => state.notifications.unreadCount)
  const isAdmin = user?.user.role === 'admin'

  useEffect(() => {
    if (user) dispatch(fetchUnreadCount())
  }, [dispatch, user])

  const displayName =
    user?.profile.firstName && user?.profile.lastName
      ? `${user.profile.firstName} ${user.profile.lastName}`
      : user?.user.username

  return (
    <header className="asa-header">
      <NavLink to="/" className="asa-header__brand">
        Agri<span className="asa-header__brand-accent">Connect</span>
      </NavLink>

      <div className="asa-header__actions">
        {user && <LanguageSwitcher className="asa-header__lang" />}
        {user && (
          <NavLink to="/explore" className="asa-header__search" aria-label={t('nav:search')}>
            <SearchIcon width={20} height={20} />
          </NavLink>
        )}
        {user && (
          <NavLink to="/messages" className="asa-header__search" aria-label={t('nav:messages')}>
            <MessageIcon width={20} height={20} />
          </NavLink>
        )}
        {user && (
          <NavLink to="/notifications" className="asa-header__search" aria-label={t('nav:notifications')}>
            <HeartIcon width={20} height={20} />
            {unreadCount > 0 && (
              <span className="asa-header__badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
            )}
          </NavLink>
        )}
        {user && (
          <Dropdown
            label={t('nav:accountMenu')}
            trigger={
              <span className="asa-header__user">
                <Avatar
                  imageUrl={user.profile.profileImageUrl}
                  name={displayName}
                  username={user.user.username}
                  size="sm"
                />
              </span>
            }
            items={[
              {
                label: t('nav:myProfile'),
                onSelect: () => navigate('/profile'),
              },
              {
                label: t('nav:saved'),
                onSelect: () => navigate('/saved'),
              },
              {
                label: t('nav:communities'),
                onSelect: () => navigate('/communities'),
              },
              {
                label: t('nav:farmclips'),
                onSelect: () => navigate('/farmclips'),
              },
              ...(isAdmin
                ? [{ label: t('nav:adminDashboard'), onSelect: () => navigate('/admin') }]
                : []),
              {
                label: t('common:buttons.logOut'),
                danger: true,
                onSelect: () => {
                  logout()
                  navigate('/login')
                },
              },
            ]}
          />
        )}
      </div>
    </header>
  )
}
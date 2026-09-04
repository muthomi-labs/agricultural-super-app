import {
  BookmarkIcon,
  ClapperIcon,
  CommunityIcon,
  CompassIcon,
  HeartIcon,
  HomeIcon,
  MessageIcon,
  PlusIcon,
  ShieldIcon,
  UserIcon,
  UsersIcon,
} from '@/components/icons'

/** Primary navigation for the app shell's desktop left sidebar (`Sidebar.jsx`).
 * `adminOnly` items are filtered out for non-admins -- this is the UX layer
 * only; the real access control is server-side (admin_required).
 * `labelKey` is looked up in the "nav" i18next namespace at render time
 * (see Sidebar.jsx/BottomNav.jsx) -- this module is plain data, not a
 * component, so it can't call useTranslation() itself. */
export const sidebarNavItems = [
  { to: '/', labelKey: 'home', icon: <HomeIcon /> },
  { to: '/explore', labelKey: 'explore', icon: <CompassIcon /> },
  { to: '/create', labelKey: 'create', icon: <PlusIcon /> },
  { to: '/farmclips', labelKey: 'farmclips', icon: <ClapperIcon /> },
  { to: '/communities', labelKey: 'communities', icon: <CommunityIcon /> },
  { to: '/experts', labelKey: 'experts', icon: <UsersIcon /> },
  { to: '/messages', labelKey: 'messages', icon: <MessageIcon /> },
  { to: '/notifications', labelKey: 'notifications', icon: <HeartIcon /> },
  { to: '/saved', labelKey: 'saved', icon: <BookmarkIcon /> },
  { to: '/profile', labelKey: 'profile', icon: <UserIcon /> },
  { to: '/admin', labelKey: 'admin', icon: <ShieldIcon />, adminOnly: true },
]

/**
 * Bottom navigation shown on small screens (mobile-first per design).
 * Everything not reachable from these five tabs is one tap away from the
 * header's search/messages/notifications icons or the account menu (see
 * Header.jsx) -- there is no separate "more" screen.
 */
export const bottomNavItems = [
  { to: '/', labelKey: 'home', icon: <HomeIcon /> },
  { to: '/explore', labelKey: 'explore', icon: <CompassIcon /> },
  { to: '/create', labelKey: 'create', icon: <PlusIcon /> },
  { to: '/notifications', labelKey: 'activity', icon: <HeartIcon /> },
  { to: '/profile', labelKey: 'profile', icon: <UserIcon /> },
]

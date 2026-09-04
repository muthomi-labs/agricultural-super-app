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
 * only; the real access control is server-side (admin_required). */
export const sidebarNavItems = [
  { to: '/', label: 'Home', icon: <HomeIcon /> },
  { to: '/explore', label: 'Explore', icon: <CompassIcon /> },
  { to: '/create', label: 'Create', icon: <PlusIcon /> },
  { to: '/farmclips', label: 'FarmClips', icon: <ClapperIcon /> },
  { to: '/communities', label: 'Communities', icon: <CommunityIcon /> },
  { to: '/experts', label: 'Experts', icon: <UsersIcon /> },
  { to: '/messages', label: 'Messages', icon: <MessageIcon /> },
  { to: '/notifications', label: 'Notifications', icon: <HeartIcon /> },
  { to: '/saved', label: 'Saved', icon: <BookmarkIcon /> },
  { to: '/profile', label: 'Profile', icon: <UserIcon /> },
  { to: '/admin', label: 'Admin', icon: <ShieldIcon />, adminOnly: true },
]

/**
 * Bottom navigation shown on small screens (mobile-first per design).
 * Everything not reachable from these five tabs is one tap away from the
 * header's search/messages/notifications icons or the account menu (see
 * Header.jsx) -- there is no separate "more" screen.
 */
export const bottomNavItems = [
  { to: '/', label: 'Home', icon: <HomeIcon /> },
  { to: '/explore', label: 'Explore', icon: <CompassIcon /> },
  { to: '/create', label: 'Create', icon: <PlusIcon /> },
  { to: '/notifications', label: 'Activity', icon: <HeartIcon /> },
  { to: '/profile', label: 'Profile', icon: <UserIcon /> },
]

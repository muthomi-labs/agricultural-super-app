import { lazy, Suspense } from 'react'
import { Navigate, createBrowserRouter, RouterProvider } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { EmptyState, Button, LoadingState } from '@/components/ui'
import { AuthProvider, useAuth } from '@/features/auth/AuthContext'
import { ProtectedRoute } from '@/features/auth/ProtectedRoute'
import { AdminRoute } from '@/features/auth/AdminRoute'
import { AppLayout } from '@/features/layout/AppLayout'
import { UnauthorizedPage } from '@/features/misc/UnauthorizedPage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { RegisterPage } from '@/features/auth/pages/RegisterPage'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/features/auth/pages/ResetPasswordPage'
import { FeedPage } from '@/features/posts/pages/FeedPage'
import { CreatePostPage } from '@/features/posts/pages/CreatePostPage'
import { CreateReelPage } from '@/features/posts/pages/CreateReelPage'
import { CreateStoryPage } from '@/features/stories/pages/CreateStoryPage'
import { PostDetailPage } from '@/features/posts/pages/PostDetailPage'
import { SavedPostsPage } from '@/features/posts/pages/SavedPostsPage'
import { ExpertsPage } from '@/features/experts/pages/ExpertsPage'
import { ExpertProfilePage } from '@/features/experts/pages/ExpertProfilePage'
import { SearchPage } from '@/features/search/pages/SearchPage'
import { ExplorePage } from '@/features/explore/pages/ExplorePage'
import { NotificationsPage } from '@/features/notifications/pages/NotificationsPage'
import { ProfilePage } from '@/features/profile/pages/ProfilePage'
import { EditProfilePage } from '@/features/profile/pages/EditProfilePage'
import { ChangePasswordPage } from '@/features/profile/pages/ChangePasswordPage'
import { CommunitiesPage } from '@/features/communities/pages/CommunitiesPage'
import { CommunityDetailPage } from '@/features/communities/pages/CommunityDetailPage'

// Code-split: heavier, less-immediately-needed routes (frontend audit
// finding -- the whole app shipped as a single ~615kB bundle with no
// splitting). Each only downloads when actually navigated to, which
// matters most for low-bandwidth users who may never visit /admin or
// /farmclips in a given session at all.
const AdminLayout = lazy(() => import('@/features/admin/AdminLayout').then((m) => ({ default: m.AdminLayout })))
const AdminDashboardPage = lazy(() =>
  import('@/features/admin/pages/AdminDashboardPage').then((m) => ({ default: m.AdminDashboardPage })),
)
const AdminUsersPage = lazy(() =>
  import('@/features/admin/pages/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })),
)
const AdminContentPage = lazy(() =>
  import('@/features/admin/pages/AdminContentPage').then((m) => ({ default: m.AdminContentPage })),
)
const AdminReportsPage = lazy(() =>
  import('@/features/admin/pages/AdminReportsPage').then((m) => ({ default: m.AdminReportsPage })),
)
const AdminCommunitiesPage = lazy(() =>
  import('@/features/admin/pages/AdminCommunitiesPage').then((m) => ({ default: m.AdminCommunitiesPage })),
)
const FarmClipsPage = lazy(() =>
  import('@/features/farmclips/pages/FarmClipsPage').then((m) => ({ default: m.FarmClipsPage })),
)
const MessagesPage = lazy(() =>
  import('@/features/messaging/pages/MessagesPage').then((m) => ({ default: m.MessagesPage })),
)
const ConversationPage = lazy(() =>
  import('@/features/messaging/pages/ConversationPage').then((m) => ({ default: m.ConversationPage })),
)
const AiAssistantPage = lazy(() =>
  import('@/features/assistant/pages/AiAssistantPage').then((m) => ({ default: m.AiAssistantPage })),
)
const AiConversationPage = lazy(() =>
  import('@/features/assistant/pages/AiConversationPage').then((m) => ({ default: m.AiConversationPage })),
)

function lazyRoute(element) {
  return <Suspense fallback={<LoadingState />}>{element}</Suspense>
}

function NotFoundPage() {
  const { t } = useTranslation('common')
  return (
    <EmptyState
      title={t('states.pageNotFound')}
      description={t('states.pageNotFoundDescription')}
      action={<Button to="/">{t('buttons.goToFeed')}</Button>}
    />
  )
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <FeedPage /> },
          { path: 'create', element: <CreatePostPage /> },
          { path: 'create/story', element: <CreateStoryPage /> },
          { path: 'create/reel', element: <CreateReelPage /> },
          { path: 'explore', element: <ExplorePage /> },
          { path: 'search', element: <SearchPage /> },
          { path: 'notifications', element: <NotificationsPage /> },
          { path: 'posts/:postId', element: <PostDetailPage /> },
          { path: 'saved', element: <SavedPostsPage /> },
          { path: 'farmclips', element: lazyRoute(<FarmClipsPage />) },
          { path: 'experts', element: <ExpertsPage /> },
          { path: 'experts/:userId', element: <ExpertProfilePage /> },
          { path: 'communities', element: <CommunitiesPage /> },
          { path: 'communities/:communityId', element: <CommunityDetailPage /> },
          { path: 'messages', element: lazyRoute(<MessagesPage />) },
          { path: 'messages/:conversationId', element: lazyRoute(<ConversationPage />) },
          { path: 'assistant', element: lazyRoute(<AiAssistantPage />) },
          { path: 'assistant/:conversationId', element: lazyRoute(<AiConversationPage />) },
          { path: 'profile', element: <ProfilePage /> },
          { path: 'profile/edit', element: <EditProfilePage /> },
          { path: 'profile/change-password', element: <ChangePasswordPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
  {
    path: '/admin',
    element: <AdminRoute />,
    children: [
      {
        element: lazyRoute(<AdminLayout />),
        children: [
          { index: true, element: lazyRoute(<AdminDashboardPage />) },
          { path: 'users', element: lazyRoute(<AdminUsersPage />) },
          { path: 'posts', element: lazyRoute(<AdminContentPage />) },
          { path: 'reports', element: lazyRoute(<AdminReportsPage />) },
          { path: 'communities', element: lazyRoute(<AdminCommunitiesPage />) },
        ],
      },
    ],
  },
  {
    path: '/unauthorized',
    element: <UnauthorizedPage />,
  },
  {
    path: '/login',
    element: <PublicOnlyRoute element={<LoginPage />} />,
  },
  {
    path: '/register',
    element: <PublicOnlyRoute element={<RegisterPage />} />,
  },
  {
    path: '/forgot-password',
    element: <PublicOnlyRoute element={<ForgotPasswordPage />} />,
  },
  {
    // Not gated by auth status: a logged-in user may still legitimately
    // follow a reset link (e.g. from another device/session).
    path: '/reset-password',
    element: <ResetPasswordPage />,
  },
])

/** Redirects already-authenticated users away from login/register. */
function PublicOnlyRoute({ element }) {
  const { t } = useTranslation('common')
  const { status } = useAuth()
  if (status === 'loading') return <EmptyState title={t('states.loading')} />
  if (status === 'authenticated') return <Navigate to="/" replace />
  return element
}

export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
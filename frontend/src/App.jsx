import { Navigate, createBrowserRouter, RouterProvider } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { EmptyState, Button } from '@/components/ui'
import { AuthProvider, useAuth } from '@/features/auth/AuthContext'
import { ProtectedRoute } from '@/features/auth/ProtectedRoute'
import { AdminRoute } from '@/features/auth/AdminRoute'
import { AppLayout } from '@/features/layout/AppLayout'
import { AdminLayout } from '@/features/admin/AdminLayout'
import { AdminDashboardPage } from '@/features/admin/pages/AdminDashboardPage'
import { AdminUsersPage } from '@/features/admin/pages/AdminUsersPage'
import { AdminContentPage } from '@/features/admin/pages/AdminContentPage'
import { AdminReportsPage } from '@/features/admin/pages/AdminReportsPage'
import { AdminCommunitiesPage } from '@/features/admin/pages/AdminCommunitiesPage'
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
import { FarmClipsPage } from '@/features/farmclips/pages/FarmClipsPage'
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
import { MessagesPage } from '@/features/messaging/pages/MessagesPage'
import { ConversationPage } from '@/features/messaging/pages/ConversationPage'
import { AiAssistantPage } from '@/features/assistant/pages/AiAssistantPage'
import { AiConversationPage } from '@/features/assistant/pages/AiConversationPage'

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
          { path: 'farmclips', element: <FarmClipsPage /> },
          { path: 'experts', element: <ExpertsPage /> },
          { path: 'experts/:userId', element: <ExpertProfilePage /> },
          { path: 'communities', element: <CommunitiesPage /> },
          { path: 'communities/:communityId', element: <CommunityDetailPage /> },
          { path: 'messages', element: <MessagesPage /> },
          { path: 'messages/:conversationId', element: <ConversationPage /> },
          { path: 'assistant', element: <AiAssistantPage /> },
          { path: 'assistant/:conversationId', element: <AiConversationPage /> },
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
        element: <AdminLayout />,
        children: [
          { index: true, element: <AdminDashboardPage /> },
          { path: 'users', element: <AdminUsersPage /> },
          { path: 'posts', element: <AdminContentPage /> },
          { path: 'reports', element: <AdminReportsPage /> },
          { path: 'communities', element: <AdminCommunitiesPage /> },
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
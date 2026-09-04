import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, EmptyState, Tabs } from '@/components/ui'
import { useAuth } from '@/features/auth/AuthContext'
import { fetchFollowersCount, fetchMyFollowing } from '@/store/slices/expertsSlice'
import { fetchSavedPosts, fetchUserPosts } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { PostGrid } from '@/features/posts/components/PostGrid'
import { GridSkeleton } from '@/features/posts/components/GridSkeleton'
import { FollowingListModal } from '../components/FollowingListModal'
import { ProfileHero } from '../components/ProfileHero'
import '../profile.css'

export function ProfilePage() {
  const { t } = useTranslation('profile')
  const { user } = useAuth()
  const TABS = [
    { value: 'posts', label: t('tabs.posts') },
    { value: 'reels', label: t('tabs.reels') },
    { value: 'saved', label: t('tabs.saved') },
  ]
  const dispatch = useAppDispatch()
  const [tab, setTab] = useState('posts')
  const [followingModalOpen, setFollowingModalOpen] = useState(false)

  const posts = useAppSelector((state) => state.posts.userPosts)
  const postsStatus = useAppSelector((state) => state.posts.userPostsStatus)
  const savedPosts = useAppSelector((state) => state.posts.savedPosts)
  const savedPostsStatus = useAppSelector((state) => state.posts.savedPostsStatus)
  const followersCount = useAppSelector((state) => state.experts.followersCounts[user?.user.id] ?? 0)
  const followingIds = useAppSelector((state) => state.experts.followingIds)

  const textPosts = useMemo(() => posts.filter((p) => !p.videoUrl), [posts])
  const reels = useMemo(() => posts.filter((p) => p.videoUrl), [posts])

  useEffect(() => {
    if (user) {
      dispatch(fetchUserPosts(user.user.id))
      dispatch(fetchFollowersCount(user.user.id))
      dispatch(fetchMyFollowing())
    }
  }, [dispatch, user])

  useEffect(() => {
    if (user && tab === 'saved') dispatch(fetchSavedPosts())
  }, [dispatch, user, tab])

  if (!user) return null

  return (
    <>
      <ProfileHero
        profile={user}
        postsCount={posts.length}
        followersCount={followersCount}
        followingCount={followingIds.length}
        onFollowingClick={() => setFollowingModalOpen(true)}
        actions={
          <>
            <Button to="/profile/edit">{t('hero.editProfile')}</Button>
            <Button variant="secondary" to="/profile/change-password">
              {t('hero.changePassword')}
            </Button>
          </>
        }
      />

      <FollowingListModal
        open={followingModalOpen}
        onClose={() => setFollowingModalOpen(false)}
        userIds={followingIds}
      />

      <Tabs items={TABS} value={tab} onChange={setTab} className="asa-profile-tabs" />

      {tab === 'posts' && (
        <>
          {postsStatus === 'loading' && <GridSkeleton />}
          {postsStatus === 'ready' && textPosts.length === 0 && (
            <EmptyState
              title={t('empty.noPostsTitle')}
              description={t('empty.noPostsDescription')}
              action={<Button to="/create">{t('empty.writePost')}</Button>}
            />
          )}
          {postsStatus === 'ready' && textPosts.length > 0 && <PostGrid posts={textPosts} />}
        </>
      )}

      {tab === 'reels' && (
        <>
          {postsStatus === 'loading' && <GridSkeleton />}
          {postsStatus === 'ready' && reels.length === 0 && (
            <EmptyState
              title={t('empty.noReelsTitle')}
              description={t('empty.noReelsDescription')}
              action={<Button to="/create/reel">{t('empty.createReel')}</Button>}
              icon="🎬"
            />
          )}
          {postsStatus === 'ready' && reels.length > 0 && <PostGrid posts={reels} />}
        </>
      )}

      {tab === 'saved' && (
        <>
          {savedPostsStatus === 'loading' && <GridSkeleton />}
          {savedPostsStatus === 'ready' && savedPosts.length === 0 && (
            <EmptyState title={t('empty.noSavedTitle')} description={t('empty.noSavedDescription')} icon="🔖" />
          )}
          {savedPostsStatus === 'ready' && savedPosts.length > 0 && <PostGrid posts={savedPosts} />}
        </>
      )}
    </>
  )
}

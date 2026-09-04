import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, EmptyState, ErrorState, LoadingState, Tabs } from '@/components/ui'
import { fetchExpert, fetchFollowersCount, fetchMyFollowing } from '@/store/slices/expertsSlice'
import { fetchUserPosts } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { PostGrid } from '@/features/posts/components/PostGrid'
import { GridSkeleton } from '@/features/posts/components/GridSkeleton'
import { ProfileHero } from '@/features/profile/components/ProfileHero'
import { useAuth } from '@/features/auth/AuthContext'
import { FollowButton } from '../components/FollowButton'
import { MessageButton } from '../components/MessageButton'
import '@/features/experts/experts.css'

export function ExpertProfilePage() {
  const { t } = useTranslation('experts')
  const TABS = [
    { value: 'posts', label: t('profile.tabPosts') },
    { value: 'reels', label: t('profile.tabReels') },
  ]
  const { userId } = useParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { user } = useAuth()
  const [tab, setTab] = useState('posts')

  const expert = useAppSelector((state) => state.experts.expert)
  const status = useAppSelector((state) => state.experts.expertStatus)
  const error = useAppSelector((state) => state.experts.expertError)
  const posts = useAppSelector((state) => state.posts.userPosts)
  const postsStatus = useAppSelector((state) => state.posts.userPostsStatus)
  const followersCount = useAppSelector((state) => state.experts.followersCounts[Number(userId)] ?? 0)
  const followingIds = useAppSelector((state) => state.experts.followingIds)

  const textPosts = useMemo(() => posts.filter((p) => !p.videoUrl), [posts])
  const reels = useMemo(() => posts.filter((p) => p.videoUrl), [posts])
  const visible = tab === 'reels' ? reels : textPosts

  useEffect(() => {
    if (!userId) return
    const id = Number(userId)
    dispatch(fetchExpert(id))
    dispatch(fetchUserPosts(id))
    dispatch(fetchFollowersCount(id))
    dispatch(fetchMyFollowing())
  }, [dispatch, userId])

  if (status === 'loading') return <LoadingState label={t('profile.loading')} />
  if (status === 'error' || !expert) return <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchExpert(Number(userId)))} />

  return (
    <>
      <ProfileHero
        profile={expert}
        postsCount={posts.length}
        followersCount={followersCount}
        actions={
          expert.user.id === user?.user.id ? null : (
            <>
              <FollowButton
                userId={expert.user.id}
                isFollowing={followingIds.includes(expert.user.id)}
                name={
                  expert.profile.firstName && expert.profile.lastName
                    ? `${expert.profile.firstName} ${expert.profile.lastName}`
                    : expert.user.username
                }
              />
              <MessageButton userId={expert.user.id} variant="secondary" size="md" />
            </>
          )
        }
      />

      <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
        &larr; {t('profile.back')}
      </Button>

      <Tabs items={TABS} value={tab} onChange={setTab} className="asa-profile-tabs" />

      {postsStatus === 'loading' && <GridSkeleton />}
      {postsStatus === 'ready' && visible.length === 0 && (
        <EmptyState
          title={tab === 'reels' ? t('profile.noReelsTitle') : t('profile.noPostsTitle')}
          description={tab === 'reels' ? t('profile.farmerNoReels') : t('profile.expertNoPosts')}
        />
      )}
      {postsStatus === 'ready' && visible.length > 0 && <PostGrid posts={visible} />}
    </>
  )
}

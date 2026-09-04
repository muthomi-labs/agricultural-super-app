import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, EmptyState, ErrorState, Tabs } from '@/components/ui'
import { fetchFeed } from '@/store/slices/postsSlice'
import { fetchMyFollowing } from '@/store/slices/expertsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { PostCard } from '../components/PostCard'
import { StoryBar } from '../components/StoryBar'
import { SuggestedPanel } from '../components/SuggestedPanel'
import { FeedSkeleton } from '../components/PostCardSkeleton'
import '../components/posts.css'

function tipOfTheDay(tips) {
  return tips[new Date().getDate() % tips.length]
}

export function FeedPage() {
  const { t } = useTranslation('posts')
  const dispatch = useAppDispatch()
  const FEED_FILTERS = [
    { value: 'all', label: t('feed.filters.all') },
    { value: 'announcements', label: t('feed.filters.announcements') },
    { value: 'following', label: t('feed.filters.following') },
  ]
  const posts = useAppSelector((state) => state.posts.feed)
  const status = useAppSelector((state) => state.posts.feedStatus)
  const error = useAppSelector((state) => state.posts.feedError)
  const followingIds = useAppSelector((state) => state.experts.followingIds)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    dispatch(fetchFeed({ page: 1, pageSize: 10 }))
    dispatch(fetchMyFollowing())
  }, [dispatch])

  const visiblePosts = useMemo(() => {
    if (filter === 'announcements') return posts.filter((post) => post.isAnnouncement)
    if (filter === 'following') return posts.filter((post) => followingIds.includes(post.author.user.id))
    return posts
  }, [posts, filter, followingIds])

  const emptyCopy = {
    all: {
      title: t('feed.empty.allTitle'),
      description: t('feed.empty.allDescription'),
    },
    announcements: {
      title: t('feed.empty.announcementsTitle'),
      description: t('feed.empty.announcementsDescription'),
    },
    following: {
      title: t('feed.empty.followingTitle'),
      description: t('feed.empty.followingDescription'),
    },
  }[filter]

  const tips = t('feed.tips', { returnObjects: true })

  return (
    <div className="asa-feed-layout">
      <div className="asa-feed-layout__main">
        <p className="asa-feed-tip">
          <strong>🌱 {t('feed.farmingTip')}</strong> {tipOfTheDay(tips)}
        </p>

        <StoryBar />

        <Tabs items={FEED_FILTERS} value={filter} onChange={setFilter} className="asa-feed-filters" />

        {status === 'loading' && <FeedSkeleton />}
        {status === 'error' && <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchFeed({ page: 1, pageSize: 10 }))} />}
        {status === 'ready' && visiblePosts.length === 0 && (
          <EmptyState
            title={emptyCopy.title}
            description={emptyCopy.description}
            action={filter === 'all' ? <Button to="/create">{t('feed.empty.writePost')}</Button> : undefined}
          />
        )}
        {status === 'ready' &&
          visiblePosts.map((post) => <PostCard key={post.id} post={post} />)}
      </div>

      <SuggestedPanel />
    </div>
  )
}

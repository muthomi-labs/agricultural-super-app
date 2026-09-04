import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { EmptyState, ErrorState, PageHeader, Tabs } from '@/components/ui'
import { fetchSavedPosts } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { PostGrid } from '../components/PostGrid'
import { GridSkeleton } from '../components/GridSkeleton'

export function SavedPostsPage() {
  const { t } = useTranslation('posts')
  const TABS = [
    { value: 'posts', label: t('saved.tabPosts') },
    { value: 'reels', label: t('saved.tabReels') },
  ]
  const dispatch = useAppDispatch()
  const savedPosts = useAppSelector((state) => state.posts.savedPosts)
  const status = useAppSelector((state) => state.posts.savedPostsStatus)
  const error = useAppSelector((state) => state.posts.savedPostsError)
  const [tab, setTab] = useState('posts')

  useEffect(() => {
    dispatch(fetchSavedPosts())
  }, [dispatch])

  const savedReels = useMemo(() => savedPosts.filter((p) => p.videoUrl), [savedPosts])
  const savedTextPosts = useMemo(() => savedPosts.filter((p) => !p.videoUrl), [savedPosts])
  const visible = tab === 'reels' ? savedReels : savedTextPosts

  return (
    <>
      <PageHeader title={t('saved.title')} subtitle={t('saved.subtitle')} />

      {status === 'loading' && <GridSkeleton />}
      {status === 'error' && <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchSavedPosts())} />}

      {status === 'ready' && (
        <>
          <Tabs items={TABS} value={tab} onChange={setTab} className="asa-profile-tabs" />
          {visible.length === 0 ? (
            <EmptyState
              title={tab === 'reels' ? t('saved.noSavedReels') : t('saved.noSavedPosts')}
              description={t('saved.description')}
              icon="🔖"
            />
          ) : (
            <PostGrid posts={visible} />
          )}
        </>
      )}
    </>
  )
}

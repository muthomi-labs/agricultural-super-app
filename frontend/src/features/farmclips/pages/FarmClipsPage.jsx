import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { EmptyState, ErrorState } from '@/components/ui'
import { fetchReels } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { ReelCard } from '../components/ReelCard'
import '../farmclips.css'

export function FarmClipsPage() {
  const { t } = useTranslation('reels')
  const dispatch = useAppDispatch()
  const reels = useAppSelector((state) => state.posts.reels)
  const status = useAppSelector((state) => state.posts.reelsStatus)
  const error = useAppSelector((state) => state.posts.reelsError)
  const [muted, setMuted] = useState(true)

  useEffect(() => {
    dispatch(fetchReels({ page: 1, pageSize: 20 }))
  }, [dispatch])

  return (
    <div className="asa-reels-page">
      {status === 'loading' && (
        <div className="asa-reels-page__state">
          <span>{t('loading')}</span>
        </div>
      )}
      {status === 'error' && (
        <div className="asa-reels-page__state">
          <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchReels({ page: 1, pageSize: 20 }))} />
        </div>
      )}
      {status === 'ready' && reels.length === 0 && (
        <div className="asa-reels-page__state">
          <EmptyState
            icon="🎬"
            title={t('empty.title')}
            description={t('empty.description')}
          />
        </div>
      )}
      {status === 'ready' &&
        reels.map((reel) => (
          <ReelCard key={reel.id} reel={reel} muted={muted} onToggleMute={() => setMuted((m) => !m)} />
        ))}
    </div>
  )
}

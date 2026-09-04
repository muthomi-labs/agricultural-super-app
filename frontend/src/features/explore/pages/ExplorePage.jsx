import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { EmptyState, ErrorState, Input, LoadingState, PageHeader } from '@/components/ui'
import { SearchIcon } from '@/components/icons'
import { errorMessage } from '@/features/auth/AuthContext'
import { ExpertCard } from '@/features/experts/components/ExpertCard'
import { CommunityCard } from '@/features/communities/components/CommunityCard'
import { PostGrid } from '@/features/posts/components/PostGrid'
import { GridSkeleton } from '@/features/posts/components/GridSkeleton'
import { fetchExperts, fetchMyFollowing } from '@/store/slices/expertsSlice'
import { fetchCommunities } from '@/store/slices/communitiesSlice'
import { fetchFeed } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { usersService } from '@/services'
import '@/features/experts/experts.css'
import '@/features/communities/communities.css'
import '@/features/search/search.css'

const DEBOUNCE_MS = 350

export function ExplorePage() {
  const { t } = useTranslation('search')
  const dispatch = useAppDispatch()
  const followingIds = useAppSelector((state) => state.experts.followingIds)
  const experts = useAppSelector((state) => state.experts.experts)
  const expertsStatus = useAppSelector((state) => state.experts.expertsStatus)
  const communities = useAppSelector((state) => state.communities.list)
  const communitiesStatus = useAppSelector((state) => state.communities.listStatus)
  const feed = useAppSelector((state) => state.posts.feed)
  const feedStatus = useAppSelector((state) => state.posts.feedStatus)

  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('idle')
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  const debounceRef = useRef(null)
  const requestIdRef = useRef(0)

  useEffect(() => {
    dispatch(fetchMyFollowing())
    dispatch(fetchExperts({ page: 1, pageSize: 6 }))
    dispatch(fetchCommunities({ page: 1, pageSize: 6 }))
    dispatch(fetchFeed({ page: 1, pageSize: 12 }))
  }, [dispatch])

  async function runSearch(term) {
    const requestId = ++requestIdRef.current
    setStatus('loading')
    try {
      const { items } = await usersService.searchUsers(term)
      if (requestId !== requestIdRef.current) return
      setResults(items)
      setStatus('ready')
    } catch (err) {
      if (requestId !== requestIdRef.current) return
      setError(errorMessage(err))
      setStatus('error')
    }
  }

  useEffect(() => {
    clearTimeout(debounceRef.current)
    const term = query.trim()

    if (!term) {
      requestIdRef.current += 1
      setStatus('idle')
      setResults([])
      setError(null)
      return
    }

    setStatus('loading')
    debounceRef.current = setTimeout(() => runSearch(term), DEBOUNCE_MS)

    return () => clearTimeout(debounceRef.current)
  }, [query])

  const searching = query.trim().length > 0
  const normalizedQuery = query.trim().toLowerCase()

  const matchingCommunities = useMemo(() => {
    if (!normalizedQuery) return []
    return communities.filter(
      (c) => c.name.toLowerCase().includes(normalizedQuery) || c.description?.toLowerCase().includes(normalizedQuery),
    )
  }, [communities, normalizedQuery])

  const matchingPosts = useMemo(() => {
    if (!normalizedQuery) return []
    return feed.filter(
      (p) => p.title.toLowerCase().includes(normalizedQuery) || p.content.toLowerCase().includes(normalizedQuery),
    )
  }, [feed, normalizedQuery])

  return (
    <>
      <PageHeader title={t('explore.title')} subtitle={t('explore.subtitle')} />

      <div className="asa-search__bar">
        <Input
          label=""
          name="explore-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('explore.placeholder')}
          aria-label={t('explore.ariaLabel')}
          className="asa-search__input"
        />
        <SearchIcon width={18} height={18} className="asa-search__icon" />
      </div>

      {searching ? (
        <>
          {status === 'loading' && <LoadingState label={t('search.searching')} />}
          {status === 'error' && <ErrorState message={error ?? undefined} onRetry={() => runSearch(query.trim())} />}

          {status === 'ready' && (
            <>
              <section className="asa-community-discovery__section">
                <h2 className="asa-community-discovery__section-title">{t('explore.farmers')}</h2>
                {results.length === 0 ? (
                  <EmptyState title={t('search.noResultsTitle')} description={t('search.noResultsDescription')} />
                ) : (
                  results.map((person) => (
                    <ExpertCard
                      key={person.user.id}
                      expert={person}
                      isFollowing={followingIds.includes(person.user.id)}
                    />
                  ))
                )}
              </section>

              {matchingCommunities.length > 0 && (
                <section className="asa-community-discovery__section">
                  <h2 className="asa-community-discovery__section-title">{t('explore.communities')}</h2>
                  <div className="asa-community-grid">
                    {matchingCommunities.map((community) => (
                      <CommunityCard key={community.id} community={community} />
                    ))}
                  </div>
                </section>
              )}

              {matchingPosts.length > 0 && (
                <section className="asa-community-discovery__section">
                  <h2 className="asa-community-discovery__section-title">{t('explore.postsAndReels')}</h2>
                  <PostGrid posts={matchingPosts} />
                </section>
              )}
            </>
          )}
        </>
      ) : (
        <>
          <section className="asa-community-discovery__section">
            <h2 className="asa-community-discovery__section-title">{t('explore.farmersToFollow')}</h2>
            {expertsStatus === 'loading' && <LoadingState label={t('explore.loadingFarmers')} />}
            {expertsStatus === 'ready' && experts.length === 0 && (
              <EmptyState title={t('explore.noFarmersYet')} icon="🌾" />
            )}
            {expertsStatus === 'ready' &&
              experts
                .slice(0, 5)
                .map((expert) => (
                  <ExpertCard key={expert.user.id} expert={expert} isFollowing={followingIds.includes(expert.user.id)} />
                ))}
            {experts.length > 5 && (
              <Link to="/experts" className="asa-community-discovery__see-all">
                {t('explore.seeAllFarmers')}
              </Link>
            )}
          </section>

          <section className="asa-community-discovery__section">
            <h2 className="asa-community-discovery__section-title">{t('explore.communities')}</h2>
            {communitiesStatus === 'loading' && <LoadingState label={t('explore.loadingCommunities')} />}
            {communitiesStatus === 'ready' && communities.length === 0 && (
              <EmptyState title={t('explore.noCommunitiesYet')} icon="🌽" />
            )}
            {communitiesStatus === 'ready' && communities.length > 0 && (
              <div className="asa-community-grid">
                {communities.slice(0, 6).map((community) => (
                  <CommunityCard key={community.id} community={community} />
                ))}
              </div>
            )}
            <Link to="/communities" className="asa-community-discovery__see-all">
              {t('explore.seeAllCommunities')}
            </Link>
          </section>

          <section className="asa-community-discovery__section">
            <h2 className="asa-community-discovery__section-title">{t('explore.recentPostsAndReels')}</h2>
            {feedStatus === 'loading' && <GridSkeleton />}
            {feedStatus === 'ready' && feed.length === 0 && <EmptyState title={t('explore.noPostsYet')} icon="🌱" />}
            {feedStatus === 'ready' && feed.length > 0 && <PostGrid posts={feed} />}
          </section>
        </>
      )}
    </>
  )
}

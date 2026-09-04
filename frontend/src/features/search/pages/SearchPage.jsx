import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { EmptyState, ErrorState, Input, LoadingState, PageHeader } from '@/components/ui'
import { SearchIcon } from '@/components/icons'
import { errorMessage } from '@/features/auth/AuthContext'
import { ExpertCard } from '@/features/experts/components/ExpertCard'
import { fetchMyFollowing } from '@/store/slices/expertsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { usersService } from '@/services'
import '../search.css'

const DEBOUNCE_MS = 350

export function SearchPage() {
  const { t } = useTranslation('search')
  const dispatch = useAppDispatch()
  const followingIds = useAppSelector((state) => state.experts.followingIds)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('idle')
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  const debounceRef = useRef(null)
  const requestIdRef = useRef(0)

  useEffect(() => {
    dispatch(fetchMyFollowing())
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

  return (
    <>
      <PageHeader title={t('search.title')} subtitle={t('search.subtitle')} />

      <div className="asa-search__bar">
        <Input
          label=""
          name="userSearch"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('search.placeholder')}
          aria-label={t('search.ariaLabel')}
          className="asa-search__input"
          autoFocus
        />
        <SearchIcon width={18} height={18} className="asa-search__icon" />
      </div>

      {status === 'idle' && (
        <EmptyState
          title={t('search.idleTitle')}
          description={t('search.idleDescription')}
          icon="🔍"
        />
      )}

      {status === 'loading' && <LoadingState label={t('search.searching')} />}

      {status === 'error' && (
        <ErrorState message={error ?? undefined} onRetry={() => runSearch(query.trim())} />
      )}

      {status === 'ready' && results.length === 0 && (
        <EmptyState
          title={t('search.noResultsTitle')}
          description={t('search.noResultsDescription')}
        />
      )}

      {status === 'ready' &&
        results.map((person) => (
          <ExpertCard
            key={person.user.id}
            expert={person}
            isFollowing={followingIds.includes(person.user.id)}
          />
        ))}
    </>
  )
}

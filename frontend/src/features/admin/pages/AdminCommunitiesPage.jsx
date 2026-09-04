import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, EmptyState, ErrorState, LoadingState, Modal, PageHeader } from '@/components/ui'
import { errorMessage } from '@/features/auth/AuthContext'
import { communitiesService } from '@/services'
import '../admin.css'

export function AdminCommunitiesPage() {
  const { t } = useTranslation('admin')
  const [communities, setCommunities] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(null)

  function load() {
    setStatus('loading')
    communitiesService
      .listCommunities(1, 50)
      .then((result) => {
        setCommunities(result.items)
        setStatus('ready')
      })
      .catch((err) => {
        setError(errorMessage(err))
        setStatus('error')
      })
  }

  useEffect(load, [])

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await communitiesService.deleteCommunity(pendingDelete.id)
      setCommunities((prev) => prev.filter((c) => c.id !== pendingDelete.id))
      setPendingDelete(null)
    } catch (err) {
      setDeleteError(errorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <PageHeader title={t('communities.title')} subtitle={t('communities.subtitle')} />

      {status === 'loading' && <LoadingState label={t('communities.loading')} />}
      {status === 'error' && <ErrorState message={error ?? undefined} onRetry={load} />}
      {status === 'ready' && communities.length === 0 && <EmptyState title={t('communities.noCommunitiesYet')} icon="👥" />}

      {status === 'ready' && communities.length > 0 && (
        <div className="asa-admin-list">
          {communities.map((community) => (
            <div key={community.id} className="asa-admin-list-row">
              <div className="asa-admin-list-row__body">
                <Link to={`/communities/${community.id}`} className="asa-admin-list-row__title">
                  {community.name}
                </Link>
                <span className="asa-admin-list-row__meta">
                  {t('communities.createdByMeta', {
                    name: community.creator.user.username,
                    count: community.members.length,
                  })}
                </span>
              </div>
              <Button variant="danger" size="sm" onClick={() => setPendingDelete(community)}>
                {t('communities.delete')}
              </Button>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={!!pendingDelete}
        title={t('communities.deleteTitle')}
        onClose={() => {
          setPendingDelete(null)
          setDeleteError(null)
        }}
      >
        <p>
          {t('communities.deleteBody', {
            name: pendingDelete?.name,
            count: pendingDelete?.members.length,
          })}
        </p>
        {deleteError && (
          <p className="asa-form-error" role="alert">
            {deleteError}
          </p>
        )}
        <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
          <Button variant="danger" loading={deleting} onClick={confirmDelete}>
            {t('communities.deleteCommunity')}
          </Button>
          <Button variant="ghost" onClick={() => setPendingDelete(null)}>
            {t('communities.cancel')}
          </Button>
        </div>
      </Modal>
    </>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, EmptyState, ErrorState, LoadingState, Modal, PageHeader } from '@/components/ui'
import { formatRelativeTime } from '@/lib/format'
import { errorMessage } from '@/features/auth/AuthContext'
import { postsService } from '@/services'
import '../admin.css'

export function AdminContentPage() {
  const { t } = useTranslation('admin')
  const [posts, setPosts] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(null)

  function load() {
    setStatus('loading')
    postsService
      .listPosts(1, 50)
      .then((result) => {
        setPosts(result.items)
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
      await postsService.deletePost(pendingDelete.id)
      setPosts((prev) => prev.filter((p) => p.id !== pendingDelete.id))
      setPendingDelete(null)
    } catch (err) {
      setDeleteError(errorMessage(err))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <PageHeader title={t('content.title')} subtitle={t('content.subtitle')} />

      {status === 'loading' && <LoadingState label={t('content.loading')} />}
      {status === 'error' && <ErrorState message={error ?? undefined} onRetry={load} />}
      {status === 'ready' && posts.length === 0 && <EmptyState title={t('content.noPostsYet')} icon="📝" />}

      {status === 'ready' && posts.length > 0 && (
        <div className="asa-admin-list">
          {posts.map((post) => (
            <div key={post.id} className="asa-admin-list-row">
              <div className="asa-admin-list-row__body">
                <Link to={`/posts/${post.id}`} className="asa-admin-list-row__title">
                  {post.title}
                </Link>
                <span className="asa-admin-list-row__meta">
                  {t('content.byMeta', {
                    name: post.author.user.username,
                    time: formatRelativeTime(post.createdAt),
                    likes: post.likeCount,
                    comments: post.comments.length,
                  })}
                </span>
              </div>
              <Button variant="danger" size="sm" onClick={() => setPendingDelete(post)}>
                {t('content.delete')}
              </Button>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={!!pendingDelete}
        title={t('content.deleteTitle')}
        onClose={() => {
          setPendingDelete(null)
          setDeleteError(null)
        }}
      >
        <p>
          {t('content.deleteBody', {
            title: pendingDelete?.title,
            name: pendingDelete?.author.user.username,
          })}
        </p>
        {deleteError && (
          <p className="asa-form-error" role="alert">
            {deleteError}
          </p>
        )}
        <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
          <Button variant="danger" loading={deleting} onClick={confirmDelete}>
            {t('content.deletePost')}
          </Button>
          <Button variant="ghost" onClick={() => setPendingDelete(null)}>
            {t('content.cancel')}
          </Button>
        </div>
      </Modal>
    </>
  )
}

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Dropdown, Modal, Textarea } from '@/components/ui'
import { MoreIcon } from '@/components/icons'
import { errorMessage, useAuth } from '@/features/auth/AuthContext'
import { deletePost, updatePost } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { ReportPostModal } from './ReportPostModal'

function canModifyPost(post, user) {
  if (!user) return false
  return post.author.user.id === user.user.id || user.user.role === 'admin'
}

function canDeletePost(post, user, community) {
  if (canModifyPost(post, user)) return true
  if (post.communityId && community?.id === post.communityId && community.myRole === 'admin') return true
  return false
}

function EditPostModal({ post, open, onClose }) {
  const { t } = useTranslation('posts')
  const dispatch = useAppDispatch()
  const [content, setContent] = useState(post.content)
  const [fieldError, setFieldError] = useState(null)
  const [error, setError] = useState(null)
  const saving = useAppSelector((state) => state.posts.updateLoadingPostId === post.id)

  function handleClose() {
    setContent(post.content)
    setFieldError(null)
    setError(null)
    onClose()
  }

  async function handleSave() {
    if (!content.trim()) {
      setFieldError(t('menu.pleaseAddContent'))
      return
    }
    setFieldError(null)
    setError(null)
    try {
      await dispatch(
        updatePost({ postId: post.id, title: post.title, content: content.trim() }),
      ).unwrap()
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <Modal open={open} title={t('menu.editPost')} onClose={handleClose}>
      <Textarea
        label={t('menu.caption')}
        name="content"
        rows={6}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        error={fieldError}
        autoFocus
      />
      {error && <p className="asa-post-menu__error">{error}</p>}
      <div className="asa-post-menu__actions">
        <Button variant="secondary" onClick={handleClose} disabled={saving}>
          {t('menu.cancel')}
        </Button>
        <Button variant="primary" onClick={handleSave} loading={saving}>
          {t('menu.saveChanges')}
        </Button>
      </div>
    </Modal>
  )
}

export function PostMenu({ post, onDeleted }) {
  const { t } = useTranslation('posts')
  const { user } = useAuth()
  const dispatch = useAppDispatch()
  const community = useAppSelector((state) => state.communities.current)
  const [editOpen, setEditOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [error, setError] = useState(null)
  const deleting = useAppSelector((state) => state.posts.deleteLoadingPostId === post.id)

  const canEdit = canModifyPost(post, user)
  const canDelete = canDeletePost(post, user, community)
  const canReport = Boolean(user) && post.author.user.id !== user.user.id
  if (!canEdit && !canDelete && !canReport) return null

  async function handleConfirmDelete() {
    setError(null)
    try {
      await dispatch(deletePost(post.id)).unwrap()
      setConfirmOpen(false)
      onDeleted?.()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const items = []
  if (canEdit) items.push({ label: t('menu.edit'), onSelect: () => setEditOpen(true) })
  if (canDelete) items.push({ label: t('menu.delete'), danger: true, onSelect: () => setConfirmOpen(true) })
  if (canReport) items.push({ label: t('menu.report'), onSelect: () => setReportOpen(true) })

  return (
    <>
      <Dropdown label={t('menu.options')} trigger={<MoreIcon width={18} height={18} />} items={items} />
      {canEdit && <EditPostModal post={post} open={editOpen} onClose={() => setEditOpen(false)} />}
      {canReport && <ReportPostModal postId={post.id} open={reportOpen} onClose={() => setReportOpen(false)} />}
      <Modal open={confirmOpen} title={t('menu.deletePostTitle')} onClose={() => setConfirmOpen(false)}>
        <p>{t('menu.deletePostBody')}</p>
        {error && <p className="asa-post-menu__error">{error}</p>}
        <div className="asa-post-menu__actions">
          <Button variant="secondary" onClick={() => setConfirmOpen(false)} disabled={deleting}>
            {t('menu.cancel')}
          </Button>
          <Button variant="danger" onClick={handleConfirmDelete} loading={deleting}>
            {t('menu.confirmDelete')}
          </Button>
        </div>
      </Modal>
    </>
  )
}

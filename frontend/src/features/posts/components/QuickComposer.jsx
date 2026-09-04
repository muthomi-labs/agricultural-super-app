import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Textarea } from '@/components/ui'
import { errorMessage } from '@/features/auth/AuthContext'
import { createPost } from '@/store/slices/postsSlice'
import { useAppDispatch } from '@/store/hooks'
import { deriveTitle } from '@/lib/format'
import './posts.css'

export function QuickComposer({ communityId, placeholder, allowAnnouncement = false, onPosted }) {
  const { t } = useTranslation('posts')
  const dispatch = useAppDispatch()
  const resolvedPlaceholder = placeholder ?? t('quickComposer.defaultPlaceholder')
  const [content, setContent] = useState('')
  const [isAnnouncement, setIsAnnouncement] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    const trimmed = content.trim()
    if (!trimmed || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const post = await dispatch(
        createPost({ title: deriveTitle(trimmed), content: trimmed, communityId, isAnnouncement }),
      ).unwrap()
      setContent('')
      setIsAnnouncement(false)
      onPosted?.(post)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="asa-quick-composer" onSubmit={handleSubmit}>
      <Textarea
        label=""
        name="quick-post"
        rows={2}
        value={content}
        onChange={(event) => setContent(event.target.value)}
        placeholder={resolvedPlaceholder}
        aria-label={resolvedPlaceholder}
      />
      {allowAnnouncement && (
        <label className="asa-quick-composer__announcement">
          <input
            type="checkbox"
            checked={isAnnouncement}
            onChange={(event) => setIsAnnouncement(event.target.checked)}
          />
          <span>📢 {t('quickComposer.postAsAnnouncement')}</span>
        </label>
      )}
      {error && (
        <p className="asa-form-error" role="alert">
          {error}
        </p>
      )}
      <div className="asa-quick-composer__actions">
        <Button
          variant="ghost"
          size="sm"
          to={communityId ? `/create?communityId=${communityId}` : '/create'}
        >
          {t('quickComposer.addPhotos')}
        </Button>
        <Button type="submit" size="sm" loading={submitting} disabled={!content.trim()}>
          {t('quickComposer.post')}
        </Button>
      </div>
    </form>
  )
}

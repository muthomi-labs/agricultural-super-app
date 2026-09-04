import { Fragment, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Avatar, Button, Modal, Textarea, VerifiedBadge } from '@/components/ui'
import { formatRelativeTime } from '@/lib/format'
import { addComment } from '@/store/slices/postsSlice'
import { useAppDispatch } from '@/store/hooks'
import { errorMessage } from '@/features/auth/AuthContext'
import './posts.css'

function commentName(comment) {
  return comment.author.profile.firstName && comment.author.profile.lastName
    ? `${comment.author.profile.firstName} ${comment.author.profile.lastName}`
    : comment.author.user.username
}

function buildCommentTree(comments) {
  const byParent = new Map()
  for (const comment of comments) {
    const key = comment.parentCommentId ?? null
    if (!byParent.has(key)) byParent.set(key, [])
    byParent.get(key).push(comment)
  }
  return { topLevel: byParent.get(null) ?? [], repliesFor: (id) => byParent.get(id) ?? [] }
}

function CommentRow({ comment, onReply, depth = 0 }) {
  const { t } = useTranslation('posts')
  return (
    <li className={`asa-comment ${depth > 0 ? 'asa-comment--reply' : ''}`}>
      <Avatar
        imageUrl={comment.author.profile.profileImageUrl}
        name={commentName(comment)}
        username={comment.author.user.username}
        size="sm"
      />
      <div className="asa-comment__body">
        <div className="asa-comment__meta">
          <strong>{commentName(comment)}</strong>
          <VerifiedBadge profile={comment.author.profile} />
          <span className="asa-comment__time">{formatRelativeTime(comment.createdAt)}</span>
        </div>
        <p className="asa-comment__content">{comment.content}</p>
        <button type="button" className="asa-comment__reply-trigger" onClick={() => onReply(comment)}>
          {t('comments.reply')}
        </button>
      </div>
    </li>
  )
}

export function CommentSection({ post }) {
  const { t } = useTranslation('posts')
  const dispatch = useAppDispatch()
  const [open, setOpen] = useState(false)
  const [content, setContent] = useState('')
  const [replyingTo, setReplyingTo] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const { topLevel, repliesFor } = useMemo(() => buildCommentTree(post.comments), [post.comments])

  function openComposer(parentComment = null) {
    setReplyingTo(parentComment)
    setOpen(true)
  }

  function closeComposer() {
    setOpen(false)
    setReplyingTo(null)
    setContent('')
    setError(null)
  }

  async function handleSubmit() {
    if (submitting) return
    setSubmitting(true)
    setError(null)
    try {
      await dispatch(addComment({ postId: post.id, content, parentCommentId: replyingTo?.id })).unwrap()
      closeComposer()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <section className="asa-comments" aria-label={t('comments.title', { count: post.comments.length })}>
        <h3 className="asa-comments__title">{t('comments.title', { count: post.comments.length })}</h3>
        {topLevel.length === 0 ? (
          <p className="asa-comments__empty">{t('comments.empty')}</p>
        ) : (
          <ul className="asa-comments__list">
            {topLevel.map((comment) => (
              <Fragment key={comment.id}>
                <CommentRow comment={comment} onReply={openComposer} />
                {repliesFor(comment.id).map((reply) => (
                  <CommentRow key={reply.id} comment={reply} onReply={openComposer} depth={1} />
                ))}
              </Fragment>
            ))}
          </ul>
        )}

        {post.commentsOpen === false ? (
          <p className="asa-comments__closed">🔒 {t('comments.closed')}</p>
        ) : (
          <Button variant="outline" size="sm" onClick={() => openComposer(null)}>
            {t('comments.addComment')}
          </Button>
        )}
      </section>

      <Modal
        open={open}
        title={replyingTo ? t('comments.replyTo', { name: commentName(replyingTo) }) : t('comments.addComment')}
        onClose={closeComposer}
      >
        <Textarea
          label={t('comments.yourComment')}
          name="comment"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          error={error ?? undefined}
          placeholder={
            replyingTo ? t('comments.replyToPlaceholder', { name: commentName(replyingTo) }) : t('comments.shareThoughts')
          }
          autoFocus
        />
        <Button onClick={handleSubmit} loading={submitting} disabled={!content.trim()}>
          {replyingTo ? t('comments.postReply') : t('comments.postComment')}
        </Button>
      </Modal>
    </>
  )
}

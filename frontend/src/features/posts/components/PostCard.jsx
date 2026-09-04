import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Badge, Button, PostContent, ReactionPicker, RepostButton, SaveButton, ShareButton, VerifiedBadge } from '@/components/ui'
import { CommentIcon, RepeatIcon } from '@/components/icons'
import { formatRelativeTime } from '@/lib/format'
import { addComment, removeReaction, setReaction, toggleRepost, toggleSave } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { PostMenu } from './PostMenu'
import { PostMedia } from './PostMedia'

function displayName(actor) {
  return actor.profile.firstName && actor.profile.lastName
    ? `${actor.profile.firstName} ${actor.profile.lastName}`
    : actor.user.username
}

function PostBody({ post, onDoubleTapMedia }) {
  return (
    <>
      <h2 className="asa-post-card__title">
        <Link to={`/posts/${post.id}`}>{post.title}</Link>
      </h2>
      <PostContent content={post.content} className="asa-post-card__excerpt" />
      <PostMedia images={post.images} videoUrl={post.videoUrl} onDoubleTap={onDoubleTapMedia} />
    </>
  )
}

function InlineAddComment({ postId, commentsOpen }) {
  const { t } = useTranslation('posts')
  const dispatch = useAppDispatch()
  const [value, setValue] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (commentsOpen === false) return null

  async function handleSubmit(event) {
    event.preventDefault()
    const content = value.trim()
    if (!content || submitting) return
    setSubmitting(true)
    try {
      await dispatch(addComment({ postId, content })).unwrap()
      setValue('')
    } catch {
      // Inline errors stay silent here -- the full thread on the post
      // detail page (CommentSection) surfaces failures explicitly.
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="asa-post-card__add-comment" onSubmit={handleSubmit}>
      <input
        type="text"
        className="asa-post-card__add-comment-input"
        placeholder={t('card.addCommentPlaceholder')}
        aria-label={t('card.addComment')}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        disabled={submitting}
      />
      <button
        type="submit"
        className="asa-post-card__add-comment-submit"
        disabled={!value.trim() || submitting}
      >
        {t('card.post')}
      </button>
    </form>
  )
}

export function PostCard({ post }) {
  const { t } = useTranslation(['posts', 'common'])
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const reactionLoading = useAppSelector((state) => state.posts.reactionLoadingPostId === post.id)
  const saveLoading = useAppSelector((state) => state.posts.saveLoadingPostId === post.id)
  const repostLoading = useAppSelector((state) => state.posts.repostLoadingPostId === post.id)

  const authorName = displayName(post.author)
  const displayedPost = post.originalPost ?? post
  const commentCount = post.comments.length

  function handleDoubleTapLike() {
    if (!post.myReaction) dispatch(setReaction({ postId: post.id, reactionType: 'love' }))
  }

  return (
    <article className="asa-post-card asa-card">
      <header className="asa-post-card__header">
        <Avatar imageUrl={post.author.profile.profileImageUrl} name={authorName} username={post.author.user.username} size="md" />
        <div className="asa-post-card__meta">
          <div className="asa-post-card__author">
            <Link to={`/experts/${post.author.user.id}`} className="asa-post-card__name">
              {authorName}
            </Link>
            <VerifiedBadge profile={post.author.profile} />
            <Badge variant="default">{t(`common:roles.${post.author.user.role}`)}</Badge>
          </div>
          <span className="asa-post-card__time">
            {post.author.profile.location ? `${post.author.profile.location} · ` : ''}
            {formatRelativeTime(post.createdAt)}
          </span>
        </div>
        <div className="asa-post-card__menu">
          <PostMenu post={post} />
        </div>
      </header>

      {post.originalPost && (
        <p className="asa-post-card__repost-note">
          <RepeatIcon width={14} height={14} /> {t('card.repostedFrom')} {displayName(post.originalPost.author)}
        </p>
      )}

      {post.content && post.originalPost && (
        <PostContent content={post.content} className="asa-post-card__excerpt" />
      )}

      {displayedPost.isAnnouncement && (
        <span className="asa-post-card__announcement">📢 {t('card.announcement')}</span>
      )}
      {displayedPost.videoUrl && <span className="asa-post-card__reel-badge">🎬 {t('card.reel')}</span>}

      {post.originalPost ? (
        <div className="asa-post-card__reposted">
          <PostBody post={post.originalPost} onDoubleTapMedia={handleDoubleTapLike} />
        </div>
      ) : (
        <PostBody post={post} onDoubleTapMedia={handleDoubleTapLike} />
      )}

      <footer className="asa-post-card__footer">
        <ReactionPicker
          reactionCounts={post.reactionCounts}
          myReaction={post.myReaction}
          loading={reactionLoading}
          onReact={(reactionType) => dispatch(setReaction({ postId: post.id, reactionType }))}
          onRemove={() => dispatch(removeReaction(post.id))}
        />
        <Button
          variant="ghost"
          size="sm"
          className="asa-post__action"
          onClick={() => navigate(`/posts/${post.id}#comments`)}
        >
          <CommentIcon width={18} height={18} />
          <span>{post.comments.length}</span>
          <span className="visually-hidden">{t('card.comments')}</span>
        </Button>
        <RepostButton
          reposted={post.repostedByMe}
          count={post.repostCount}
          loading={repostLoading}
          onToggle={() => dispatch(toggleRepost(post.id))}
        />
        <ShareButton postId={post.id} />
        <SaveButton saved={post.savedByMe} loading={saveLoading} onToggle={() => dispatch(toggleSave(post.id))} />
      </footer>

      {post.likeCount > 0 && (
        <p className="asa-post-card__likes">
          {post.likeCount} {t('card.likes')}
          {post.videoUrl ? ` · ${post.viewCount} ${t('card.views')}` : ''}
        </p>
      )}

      {commentCount > 0 && (
        <Link to={`/posts/${post.id}#comments`} className="asa-post-card__view-comments">
          {t('card.viewAllComments', { count: commentCount })}
        </Link>
      )}

      <InlineAddComment postId={post.id} commentsOpen={post.commentsOpen} />
    </article>
  )
}

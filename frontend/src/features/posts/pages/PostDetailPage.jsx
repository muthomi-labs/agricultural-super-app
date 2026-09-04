import { useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Card, EmptyState, ErrorState, LoadingState, PostContent, ReactionPicker, RepostButton, SaveButton, ShareButton, VerifiedBadge } from '@/components/ui'
import { RepeatIcon } from '@/components/icons'
import { formatRelativeTime } from '@/lib/format'
import { fetchPost, removeReaction, setReaction, toggleRepost, toggleSave } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { CommentSection } from '../components/CommentSection'
import { PostMenu } from '../components/PostMenu'
import { PostMedia } from '../components/PostMedia'
import '../components/posts.css'

export function PostDetailPage() {
  const { t } = useTranslation('posts')
  const { postId } = useParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const post = useAppSelector((state) => state.posts.current)
  const status = useAppSelector((state) => state.posts.currentStatus)
  const error = useAppSelector((state) => state.posts.currentError)
  const reactionLoading = useAppSelector((state) => state.posts.reactionLoadingPostId === post?.id)
  const saveLoading = useAppSelector((state) => state.posts.saveLoadingPostId === post?.id)
  const repostLoading = useAppSelector((state) => state.posts.repostLoadingPostId === post?.id)

  useEffect(() => {
    if (postId) dispatch(fetchPost(Number(postId)))
  }, [dispatch, postId])

  if (status === 'loading') return <LoadingState label={t('detail.loading')} />
  if (status === 'error') return <ErrorState message={error ?? undefined} onRetry={() => postId && dispatch(fetchPost(Number(postId)))} />
  if (!post) return <EmptyState title={t('detail.notFound')} />

  const authorName =
    post.author.profile.firstName && post.author.profile.lastName
      ? `${post.author.profile.firstName} ${post.author.profile.lastName}`
      : post.author.user.username
  const displayedPost = post.originalPost ?? post

  return (
    <article>
      <Card className="asa-post-detail" padded>
        <header className="asa-post-card__header">
          <Avatar
            imageUrl={post.author.profile.profileImageUrl}
            name={authorName}
            username={post.author.user.username}
            size="md"
          />
          <div className="asa-post-card__meta">
            <div className="asa-post-card__author">
              <Link to={`/experts/${post.author.user.id}`} className="asa-post-card__name">
                {authorName}
              </Link>
              <VerifiedBadge profile={post.author.profile} />
            </div>
            <span className="asa-post-card__time">
              {post.author.profile.location ? `${post.author.profile.location} · ` : ''}
              {formatRelativeTime(post.createdAt)}
            </span>
          </div>
          <div className="asa-post-card__menu">
            <PostMenu post={post} onDeleted={() => navigate('/')} />
          </div>
        </header>

        {post.originalPost && (
          <p className="asa-post-card__repost-note">
            <RepeatIcon width={14} height={14} /> {t('card.repostedFrom')}{' '}
            {post.originalPost.author.profile.firstName || post.originalPost.author.user.username}
          </p>
        )}

        {displayedPost.isAnnouncement && (
          <span className="asa-post-card__announcement">📢 {t('card.announcement')}</span>
        )}

        <h1 className="asa-post-detail__title">{displayedPost.title}</h1>
        <PostContent content={displayedPost.content} className="asa-post-detail__content" />
        <PostMedia
          images={displayedPost.images}
          videoUrl={displayedPost.videoUrl}
          onDoubleTap={() => {
            if (!post.myReaction) dispatch(setReaction({ postId: post.id, reactionType: 'love' }))
          }}
        />

        <footer className="asa-post-card__footer">
          <ReactionPicker
            reactionCounts={post.reactionCounts}
            myReaction={post.myReaction}
            loading={reactionLoading}
            onReact={(reactionType) => dispatch(setReaction({ postId: post.id, reactionType }))}
            onRemove={() => dispatch(removeReaction(post.id))}
          />
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
          </p>
        )}
      </Card>

      <div id="comments">
        <CommentSection post={post} />
      </div>
    </article>
  )
}

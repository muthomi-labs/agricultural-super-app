import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Button, Modal, ReactionPicker, RepostButton, SaveButton, ShareButton } from '@/components/ui'
import { CommentIcon, EyeCountIcon, HeartIcon, PlayIcon, VolumeIcon } from '@/components/icons'
import { formatCount, splitHashtags } from '@/lib/format'
import { incrementView, removeReaction, setReaction, toggleRepost, toggleSave } from '@/store/slices/postsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { useAuth } from '@/features/auth/AuthContext'
import { FollowButton } from '@/features/experts/components/FollowButton'
import { PostMenu } from '@/features/posts/components/PostMenu'
import { CommentSection } from '@/features/posts/components/CommentSection'
import '../farmclips.css'

function displayName(actor) {
  return actor.profile.firstName && actor.profile.lastName
    ? `${actor.profile.firstName} ${actor.profile.lastName}`
    : actor.user.username
}

export function ReelCard({ reel, muted, onToggleMute }) {
  const { t } = useTranslation('reels')
  const dispatch = useAppDispatch()
  const { user } = useAuth()
  const containerRef = useRef(null)
  const videoRef = useRef(null)
  const viewedRef = useRef(false)
  const [playing, setPlaying] = useState(true)
  const [burst, setBurst] = useState(false)
  const [commentsOpen, setCommentsOpen] = useState(false)

  const reactionLoading = useAppSelector((state) => state.posts.reactionLoadingPostId === reel.id)
  const saveLoading = useAppSelector((state) => state.posts.saveLoadingPostId === reel.id)
  const repostLoading = useAppSelector((state) => state.posts.repostLoadingPostId === reel.id)
  const followingIds = useAppSelector((state) => state.experts.followingIds)

  useEffect(() => {
    const container = containerRef.current
    const video = videoRef.current
    if (!container || !video) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
          video.play().catch(() => {})
          setPlaying(true)
          if (!viewedRef.current) {
            viewedRef.current = true
            dispatch(incrementView(reel.id))
          }
        } else {
          video.pause()
          setPlaying(false)
        }
      },
      { threshold: [0, 0.6, 1] },
    )
    observer.observe(container)
    return () => observer.disconnect()
  }, [dispatch, reel.id])

  function togglePlay() {
    const video = videoRef.current
    if (!video) return
    if (video.paused) {
      video.play().catch(() => {})
      setPlaying(true)
    } else {
      video.pause()
      setPlaying(false)
    }
  }

  function handleDoubleClick() {
    if (!reel.myReaction) dispatch(setReaction({ postId: reel.id, reactionType: 'love' }))
    setBurst(false)
    requestAnimationFrame(() => setBurst(true))
  }

  const authorName = displayName(reel.author)
  const isOwnReel = user?.user.id === reel.author.user.id

  return (
    <section className="asa-reel-card" ref={containerRef}>
      <video
        ref={videoRef}
        className="asa-reel-card__video"
        src={reel.videoUrl}
        poster={reel.images[0]?.imageUrl}
        loop
        playsInline
        muted={muted}
        onClick={togglePlay}
        onDoubleClick={handleDoubleClick}
      />

      {burst && (
        <HeartIcon
          filled
          width={96}
          height={96}
          className="asa-reel-card__heart-burst"
          onAnimationEnd={() => setBurst(false)}
        />
      )}
      {!playing && <PlayIcon width={56} height={56} className="asa-reel-card__play-indicator" />}

      <button
        type="button"
        className="asa-reel-card__mute"
        onClick={onToggleMute}
        aria-label={muted ? t('unmute') : t('mute')}
      >
        <VolumeIcon muted={muted} width={20} height={20} />
      </button>

      <div className="asa-reel-card__menu">
        <PostMenu post={reel} />
      </div>

      <div className="asa-reel-card__overlay">
        <div className="asa-reel-card__creator">
          <Link to={`/experts/${reel.author.user.id}`}>
            <Avatar
              imageUrl={reel.author.profile.profileImageUrl}
              name={authorName}
              username={reel.author.user.username}
              size="md"
            />
          </Link>
          <Link to={`/experts/${reel.author.user.id}`} className="asa-reel-card__name">
            {authorName}
          </Link>
          {!isOwnReel && (
            <FollowButton
              userId={reel.author.user.id}
              isFollowing={followingIds.includes(reel.author.user.id)}
              name={authorName}
            />
          )}
        </div>

        {reel.content && (
          <p className="asa-reel-card__caption">
            {splitHashtags(reel.content).map((segment, index) =>
              segment.isHashtag ? (
                <span key={index} className="asa-reel-card__hashtag">
                  {segment.text}
                </span>
              ) : (
                <span key={index}>{segment.text}</span>
              ),
            )}
          </p>
        )}

        <span className="asa-reel-card__views">
          <EyeCountIcon width={14} height={14} /> {formatCount(reel.viewCount)} {t('views')}
        </span>
      </div>

      <div className="asa-reel-card__actions">
        <ReactionPicker
          reactionCounts={reel.reactionCounts}
          myReaction={reel.myReaction}
          loading={reactionLoading}
          onReact={(reactionType) => dispatch(setReaction({ postId: reel.id, reactionType }))}
          onRemove={() => dispatch(removeReaction(reel.id))}
        />
        <Button
          variant="ghost"
          size="sm"
          className="asa-post__action"
          onClick={() => setCommentsOpen(true)}
        >
          <CommentIcon width={20} height={20} />
          <span>{reel.comments.length}</span>
          <span className="visually-hidden">{t('comments')}</span>
        </Button>
        <RepostButton
          reposted={reel.repostedByMe}
          count={reel.repostCount}
          loading={repostLoading}
          onToggle={() => dispatch(toggleRepost(reel.id))}
        />
        <SaveButton saved={reel.savedByMe} loading={saveLoading} onToggle={() => dispatch(toggleSave(reel.id))} />
        <ShareButton postId={reel.id} />
      </div>

      <Modal open={commentsOpen} title={t('comments')} onClose={() => setCommentsOpen(false)}>
        <div className="asa-reel-comments">
          <CommentSection post={reel} />
        </div>
      </Modal>
    </section>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Button, ImageUploader, Textarea } from '@/components/ui'
import { ClapperIcon, LeafIcon } from '@/components/icons'
import { createPost } from '@/store/slices/postsSlice'
import { fetchCommunities, fetchCommunity } from '@/store/slices/communitiesSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { useAuth, errorMessage } from '@/features/auth/AuthContext'
import { deriveTitle } from '@/lib/format'
import '../components/posts.css'

function displayName(user) {
  return user.profile.firstName && user.profile.lastName
    ? `${user.profile.firstName} ${user.profile.lastName}`
    : user.user.username
}

export function CreatePostPage() {
  const { t } = useTranslation('posts')
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const communityIdFromUrl = searchParams.get('communityId') ? Number(searchParams.get('communityId')) : null

  const community = useAppSelector((state) => state.communities.current)
  const communities = useAppSelector((state) => state.communities.list)
  const myCommunities = useMemo(() => communities.filter((c) => c.myRole), [communities])

  const [content, setContent] = useState('')
  const [imageUrls, setImageUrls] = useState([])
  const [imagesUploading, setImagesUploading] = useState(false)
  const [isAnnouncement, setIsAnnouncement] = useState(false)
  const [pickedCommunityId, setPickedCommunityId] = useState('')
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (communityIdFromUrl) dispatch(fetchCommunity(communityIdFromUrl))
    else dispatch(fetchCommunities({ page: 1, pageSize: 50 }))
  }, [dispatch, communityIdFromUrl])

  const communityId = communityIdFromUrl || (pickedCommunityId ? Number(pickedCommunityId) : null)
  const activeCommunity = communityIdFromUrl
    ? (community?.id === communityIdFromUrl ? community : null)
    : myCommunities.find((c) => c.id === communityId) ?? null
  const canPostAnnouncement = Boolean(activeCommunity && activeCommunity.myRole === 'admin')

  async function handleSubmit(event) {
    event.preventDefault()
    const trimmed = content.trim()
    if (!trimmed || submitting || imagesUploading) return
    setSubmitting(true)
    setFormError(null)
    try {
      const post = await dispatch(
        createPost({
          title: deriveTitle(trimmed),
          content: trimmed,
          imageUrls,
          communityId,
          isAnnouncement: canPostAnnouncement && isAnnouncement,
        }),
      ).unwrap()
      navigate(communityId ? `/communities/${communityId}` : `/posts/${post.id}`, { replace: true })
    } catch (error) {
      setFormError(errorMessage(error))
      setSubmitting(false)
    }
  }

  const heading = communityId
    ? canPostAnnouncement && isAnnouncement
      ? t('createPost.announcementHeading')
      : t('createPost.postToHeading', { name: activeCommunity?.name ?? t('createPost.community') })
    : t('createPost.heading')

  return (
    <div className="asa-social-composer">
      <h1 className="asa-social-composer__heading">{heading}</h1>

      <form onSubmit={handleSubmit}>
        {user && (
          <div className="asa-social-composer__author">
            <Avatar imageUrl={user.profile.profileImageUrl} name={displayName(user)} username={user.user.username} size="md" />
            <strong>{displayName(user)}</strong>
          </div>
        )}

        <Textarea
          label=""
          name="content"
          aria-label={t('createPost.captionLabel')}
          rows={5}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={t('createPost.captionPlaceholder')}
          className="asa-social-composer__textarea"
          autoFocus
        />

        <ImageUploader multiple maxFiles={6} onChange={setImageUrls} onBusyChange={setImagesUploading} />

        <div className="asa-social-composer__attachments">
          <button
            type="button"
            className="asa-social-composer__attachment"
            onClick={() => navigate('/create/reel')}
          >
            <ClapperIcon width={18} height={18} />
            {t('createPost.videoReel')}
          </button>

          {myCommunities.length > 0 && !communityIdFromUrl && (
            <label className="asa-social-composer__attachment asa-social-composer__attachment--select">
              <LeafIcon width={18} height={18} />
              <select value={pickedCommunityId} onChange={(event) => setPickedCommunityId(event.target.value)}>
                <option value="">{t('createPost.yourFeed')}</option>
                {myCommunities.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {canPostAnnouncement && (
          <label className="asa-quick-composer__announcement">
            <input
              type="checkbox"
              checked={isAnnouncement}
              onChange={(event) => setIsAnnouncement(event.target.checked)}
            />
            <span>📢 {t('createPost.postAsAnnouncement')}</span>
          </label>
        )}

        {formError && <p className="asa-form-error" role="alert">{formError}</p>}

        <div className="asa-composer__submit-row">
          <Button
            type="button"
            variant="secondary"
            disabled={submitting}
            onClick={() => navigate(communityId ? `/communities/${communityId}` : '/', { replace: true })}
          >
            {t('createPost.cancel')}
          </Button>
          <Button type="submit" loading={submitting} disabled={submitting || imagesUploading || !content.trim()}>
            {imagesUploading ? t('createPost.uploadingPhotos') : t('createPost.submit')}
          </Button>
        </div>
      </form>
    </div>
  )
}

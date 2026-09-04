import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, Textarea } from '@/components/ui'
import { LeafIcon, PlayIcon } from '@/components/icons'
import { createPost } from '@/store/slices/postsSlice'
import { fetchCommunities } from '@/store/slices/communitiesSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { errorMessage } from '@/features/auth/AuthContext'
import { deriveTitle } from '@/lib/format'
import { videoFileError } from '@/lib/videoPolicy'
import { uploadsService } from '@/services'
import '../components/posts.css'

export function CreateReelPage() {
  const { t } = useTranslation('posts')
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  const communities = useAppSelector((state) => state.communities.list)
  const myCommunities = useMemo(() => communities.filter((c) => c.myRole), [communities])

  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [videoReady, setVideoReady] = useState(false)
  const [coverBlob, setCoverBlob] = useState(null)
  const [coverPreviewUrl, setCoverPreviewUrl] = useState(null)
  const [caption, setCaption] = useState('')
  const [pickedCommunityId, setPickedCommunityId] = useState('')
  const [fileError, setFileError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [publishing, setPublishing] = useState(false)
  const [progressLabel, setProgressLabel] = useState(null)

  useEffect(() => {
    dispatch(fetchCommunities({ page: 1, pageSize: 50 }))
  }, [dispatch])

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      if (coverPreviewUrl) URL.revokeObjectURL(coverPreviewUrl)
    }
  }, [previewUrl, coverPreviewUrl])

  function handleFileChange(event) {
    const selected = event.target.files?.[0]
    event.target.value = ''
    if (!selected) return

    const error = videoFileError(selected)
    if (error) {
      setFileError(error)
      return
    }

    setFileError(null)
    setFile(selected)
    setVideoReady(false)
    setCoverBlob(null)
    setCoverPreviewUrl(null)
    setPreviewUrl(URL.createObjectURL(selected))
  }

  function captureCoverFrame() {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob((blob) => {
      if (!blob) return
      setCoverBlob(blob)
      setCoverPreviewUrl(URL.createObjectURL(blob))
    }, 'image/jpeg', 0.85)
  }

  function reset() {
    setFile(null)
    setPreviewUrl(null)
    setCoverBlob(null)
    setCoverPreviewUrl(null)
  }

  async function handlePublish(event) {
    event.preventDefault()
    if (!file || publishing) return
    setPublishing(true)
    setFormError(null)
    try {
      setProgressLabel(t('createReel.uploadingVideo'))
      const { url: videoUrl } = await uploadsService.uploadVideo(file, {
        onProgress: (percent) => setProgressLabel(t('createReel.uploadingVideoPercent', { percent })),
      })

      const imageUrls = []
      if (coverBlob) {
        setProgressLabel(t('createReel.uploadingCover'))
        const coverFile = new File([coverBlob], 'cover.jpg', { type: 'image/jpeg' })
        const { url: coverUrl } = await uploadsService.uploadImage(coverFile)
        imageUrls.push(coverUrl)
      }

      setProgressLabel(t('createReel.publishing'))
      const communityId = pickedCommunityId ? Number(pickedCommunityId) : null
      const post = await dispatch(
        createPost({
          title: deriveTitle(caption.trim() || t('createReel.defaultTitle')),
          content: caption.trim(),
          videoUrl,
          imageUrls,
          communityId,
        }),
      ).unwrap()

      navigate(`/posts/${post.id}`, { replace: true })
    } catch (error) {
      setFormError(errorMessage(error))
      setProgressLabel(null)
      setPublishing(false)
    }
  }

  return (
    <div className="asa-social-composer">
      <h1 className="asa-social-composer__heading">{t('createReel.heading')}</h1>

      <form onSubmit={handlePublish}>
        {previewUrl ? (
          <div className="asa-reel-composer__preview">
            <video
              ref={videoRef}
              src={previewUrl}
              controls
              playsInline
              preload="metadata"
              onLoadedData={() => setVideoReady(true)}
            />
            <button type="button" className="asa-reel-composer__remove" onClick={reset} disabled={publishing}>
              {t('createReel.chooseDifferent')}
            </button>
          </div>
        ) : (
          <label className="asa-reel-composer__picker">
            <PlayIcon width={32} height={32} />
            <span>{t('createReel.selectVideo')}</span>
            <input type="file" accept="video/mp4,video/quicktime,video/webm" className="visually-hidden" onChange={handleFileChange} />
          </label>
        )}
        {fileError && <p className="asa-form-error" role="alert">{fileError}</p>}
        <p className="asa-field__hint">{t('createReel.fileHint')}</p>

        {previewUrl && (
          <div className="asa-reel-composer__cover">
            <span className="asa-field__label">{t('createReel.coverOptional')}</span>
            <div className="asa-reel-composer__cover-row">
              {coverPreviewUrl && <img src={coverPreviewUrl} alt="" className="asa-reel-composer__cover-preview" />}
              <Button type="button" variant="secondary" size="sm" onClick={captureCoverFrame} disabled={publishing || !videoReady}>
                {t('createReel.useCurrentFrame')}
              </Button>
            </div>
          </div>
        )}

        <Textarea
          label=""
          name="caption"
          aria-label={t('createReel.captionLabel')}
          rows={4}
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          placeholder={t('createReel.captionPlaceholder')}
          className="asa-social-composer__textarea"
        />

        {myCommunities.length > 0 && (
          <div className="asa-social-composer__attachments">
            <label className="asa-social-composer__attachment asa-social-composer__attachment--select">
              <LeafIcon width={18} height={18} />
              <select value={pickedCommunityId} onChange={(event) => setPickedCommunityId(event.target.value)}>
                <option value="">{t('createReel.yourFeed')}</option>
                {myCommunities.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}

        {formError && <p className="asa-form-error" role="alert">{formError}</p>}
        {publishing && progressLabel && <p className="asa-field__hint">{progressLabel}</p>}

        <div className="asa-composer__submit-row">
          <Button type="button" variant="secondary" disabled={publishing} onClick={() => navigate('/', { replace: true })}>
            {t('createReel.cancel')}
          </Button>
          <Button type="submit" loading={publishing} disabled={publishing || !file}>
            {t('createReel.shareReel')}
          </Button>
        </div>
      </form>

      <canvas ref={canvasRef} className="visually-hidden" />
    </div>
  )
}

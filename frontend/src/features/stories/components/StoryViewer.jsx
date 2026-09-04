import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Avatar } from '@/components/ui'
import { XIcon } from '@/components/icons'
import { asUtcDate, formatRelativeTime } from '@/lib/format'
import '../stories.css'

const SLIDE_DURATION_MS = 4500
const TICK_MS = 60

function isExpired(slide) {
  return Boolean(slide) && asUtcDate(slide.expiresAt).getTime() <= Date.now()
}

export function StoryViewer({ stories, startIndex = 0, onClose }) {
  const { t } = useTranslation('stories')
  const [userIndex, setUserIndex] = useState(startIndex)
  const [slideIndex, setSlideIndex] = useState(0)
  const [progress, setProgress] = useState(0)
  const intervalRef = useRef(null)

  const story = stories[userIndex]
  const slide = story?.slides[slideIndex]

  useEffect(() => {
    setSlideIndex(0)
    setProgress(0)
  }, [userIndex])

  // The backend is authoritative on expiration -- this only reacts to a
  // story going stale (its 24h window lapsing) *while the viewer is
  // already open*, by skipping straight past it, the same as if its
  // slide duration had simply run out.
  useEffect(() => {
    if (isExpired(slide)) goNext()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slide])

  useEffect(() => {
    setProgress(0)
    clearInterval(intervalRef.current)
    intervalRef.current = setInterval(() => {
      setProgress((value) => {
        if (value >= 100) return 100
        return value + (TICK_MS / SLIDE_DURATION_MS) * 100
      })
    }, TICK_MS)
    return () => clearInterval(intervalRef.current)
  }, [userIndex, slideIndex])

  useEffect(() => {
    if (progress < 100) return
    goNext()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [progress])

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose()
      if (event.key === 'ArrowRight') goNext()
      if (event.key === 'ArrowLeft') goPrev()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userIndex, slideIndex])

  if (!story || !slide) return null

  function goNext() {
    if (slideIndex < story.slides.length - 1) {
      setSlideIndex((i) => i + 1)
    } else if (userIndex < stories.length - 1) {
      setUserIndex((i) => i + 1)
    } else {
      onClose()
    }
  }

  function goPrev() {
    if (slideIndex > 0) {
      setSlideIndex((i) => i - 1)
    } else if (userIndex > 0) {
      setUserIndex((i) => i - 1)
    }
  }

  return (
    <div className="asa-story-viewer" role="dialog" aria-modal="true" aria-label={t('viewer.ariaLabel', { name: story.authorName })}>
      <div className="asa-story-viewer__stage">
        <div className="asa-story-viewer__progress">
          {story.slides.map((s, index) => (
            <span key={s.id} className="asa-story-viewer__progress-track">
              <span
                className={`asa-story-viewer__progress-fill ${index < slideIndex ? 'asa-story-viewer__progress-fill--done' : ''}`}
                style={index === slideIndex ? { width: `${progress}%` } : undefined}
              />
            </span>
          ))}
        </div>

        <div className="asa-story-viewer__header">
          <Avatar imageUrl={story.authorImageUrl} name={story.authorName} username={story.authorUsername} size="sm" />
          <strong>{story.authorName}</strong>
          <time>{formatRelativeTime(slide.createdAt)}</time>
          <button type="button" className="asa-story-viewer__close" onClick={onClose} aria-label={t('viewer.close')}>
            <XIcon width={16} height={16} />
          </button>
        </div>

        <div className="asa-story-viewer__media">
          <img src={slide.imageUrl} alt="" />
          {slide.caption && <p className="asa-story-viewer__caption">{slide.caption}</p>}

          <button
            type="button"
            className="asa-story-viewer__tap-zone asa-story-viewer__tap-zone--prev"
            onClick={goPrev}
            aria-label={t('viewer.previous')}
          />
          <button
            type="button"
            className="asa-story-viewer__tap-zone asa-story-viewer__tap-zone--next"
            onClick={goNext}
            aria-label={t('viewer.next')}
          />
        </div>
      </div>
    </div>
  )
}

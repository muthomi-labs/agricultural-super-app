import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { HeartIcon, LeafIcon } from '@/components/icons'

function handleImageError(event) {
  event.currentTarget.style.display = 'none'
  event.currentTarget.nextElementSibling?.removeAttribute('hidden')
}

export function PostMedia({ images = [], videoUrl, onDoubleTap }) {
  const { t } = useTranslation('posts')
  const trackRef = useRef(null)
  const [active, setActive] = useState(0)
  const [burst, setBurst] = useState(false)

  if (videoUrl) {
    return (
      <div className="asa-post-media">
        <video
          className="asa-post-media__video"
          src={videoUrl}
          poster={images[0]?.imageUrl}
          controls
          playsInline
        />
      </div>
    )
  }

  if (images.length === 0) return null

  function handleScroll() {
    const track = trackRef.current
    if (!track) return
    const index = Math.round(track.scrollLeft / track.clientWidth)
    setActive(index)
  }

  function goTo(index) {
    const track = trackRef.current
    if (!track) return
    track.scrollTo({ left: index * track.clientWidth, behavior: 'smooth' })
  }

  function handleDoubleClick() {
    if (!onDoubleTap) return
    onDoubleTap()
    setBurst(false)
    requestAnimationFrame(() => setBurst(true))
  }

  return (
    <div className="asa-post-media">
      <div className="asa-post-media__track" ref={trackRef} onScroll={handleScroll} onDoubleClick={handleDoubleClick}>
        {images.map((image) => (
          <div className="asa-post-media__slide" key={image.id}>
            <img src={image.imageUrl} alt="" loading="lazy" draggable={false} onError={handleImageError} />
            <span className="asa-post-media__fallback" hidden aria-hidden="true">
              <LeafIcon width={28} height={28} />
            </span>
          </div>
        ))}
      </div>
      {burst && (
        <HeartIcon
          filled
          width={96}
          height={96}
          className="asa-post-media__heart-burst"
          onAnimationEnd={() => setBurst(false)}
        />
      )}
      {images.length > 1 && (
        <div className="asa-post-media__dots" role="tablist" aria-label={t('media.postPhotos')}>
          {images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              role="tab"
              aria-selected={index === active}
              aria-label={t('media.photoOfCount', { index: index + 1, total: images.length })}
              className={`asa-post-media__dot ${index === active ? 'asa-post-media__dot--active' : ''}`}
              onClick={() => goTo(index)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

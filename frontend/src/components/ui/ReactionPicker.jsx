import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDownIcon, HeartIcon } from '@/components/icons'
import './ui.css'

export const REACTIONS = [
  { type: 'love', emoji: '❤️' },
  { type: 'like', emoji: '👍' },
  { type: 'funny', emoji: '😂' },
  { type: 'wow', emoji: '😮' },
  { type: 'sad', emoji: '😢' },
  { type: 'fire', emoji: '🔥' },
]

export function ReactionPicker({ reactionCounts = {}, myReaction, onReact, onRemove, loading = false }) {
  const { t } = useTranslation('posts')
  const REACTIONS_BY_TYPE = Object.fromEntries(
    REACTIONS.map((reaction) => [reaction.type, { ...reaction, label: t(`reactions.${reaction.type}`) }]),
  )
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const close = useCallback(() => setOpen(false), [])

  useEffect(() => {
    if (!open) return

    function handlePointerDown(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) close()
    }
    function handleKeyDown(event) {
      if (event.key === 'Escape') close()
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, close])

  const totalCount = Object.values(reactionCounts).reduce((sum, count) => sum + count, 0)
  const current = myReaction ? REACTIONS_BY_TYPE[myReaction] : null

  function handlePick(type) {
    close()
    if (loading) return
    if (type === myReaction) {
      onRemove()
    } else {
      onReact(type)
    }
  }

  function handleHeartClick() {
    if (loading) return
    if (current) {
      onRemove()
    } else {
      onReact('love')
    }
  }

  return (
    <div className="asa-reaction-picker" ref={rootRef}>
      <span className="asa-reaction-picker__group">
        <button
          type="button"
          className={`asa-btn asa-btn--ghost asa-btn--sm asa-post__action asa-reaction-picker__heart ${current ? 'asa-reaction-picker__trigger--active' : ''}`}
          onClick={handleHeartClick}
          aria-pressed={Boolean(current)}
          disabled={loading}
        >
          {current ? (
            <span aria-hidden="true">{current.emoji}</span>
          ) : (
            <HeartIcon width={19} height={19} />
          )}
          <span>{totalCount}</span>
          <span className="visually-hidden">
            {current ? t('reactions.removeReaction', { label: current.label }) : t('reactions.likeThisPost')}
          </span>
        </button>
        <button
          type="button"
          className="asa-reaction-picker__chevron"
          onClick={() => setOpen((value) => !value)}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label={
            current ? t('reactions.yourReaction', { label: current.label }) : t('reactions.reactToThisPost')
          }
          disabled={loading}
        >
          <ChevronDownIcon width={14} height={14} />
        </button>
      </span>

      {open && (
        <ul className="asa-reaction-picker__menu" role="menu">
          {REACTIONS.map((reaction) => {
            const label = t(`reactions.${reaction.type}`)
            return (
              <li key={reaction.type} role="none">
                <button
                  type="button"
                  role="menuitem"
                  className={`asa-reaction-picker__option ${myReaction === reaction.type ? 'asa-reaction-picker__option--active' : ''}`}
                  onClick={() => handlePick(reaction.type)}
                  aria-label={label}
                  title={label}
                >
                  {reaction.emoji}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Modal } from '@/components/ui'
import { PlusIcon } from '@/components/icons'
import './layout.css'

export function CreateButton({ variant = 'sidebar' }) {
  const { t } = useTranslation('nav')
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  function choose(path) {
    setOpen(false)
    navigate(path)
  }

  return (
    <>
      {variant === 'sidebar' ? (
        <button type="button" className="asa-sidebar__link asa-sidebar__link--button" onClick={() => setOpen(true)}>
          <PlusIcon />
          <span>{t('create')}</span>
        </button>
      ) : (
        <button
          type="button"
          className="asa-bottom-nav__create"
          onClick={() => setOpen(true)}
          aria-label={t('create')}
        >
          <PlusIcon width={22} height={22} />
        </button>
      )}

      <Modal open={open} title={t('createMenu.title')} onClose={() => setOpen(false)}>
        <div className="asa-create-menu">
          <button type="button" className="asa-create-menu__option" onClick={() => choose('/create')}>
            <span className="asa-create-menu__icon" aria-hidden="true">
              📝
            </span>
            <span className="asa-create-menu__text">
              <strong>{t('createMenu.post')}</strong>
              <small>{t('createMenu.postDescription')}</small>
            </span>
          </button>
          <button type="button" className="asa-create-menu__option" onClick={() => choose('/create/story')}>
            <span className="asa-create-menu__icon" aria-hidden="true">
              📸
            </span>
            <span className="asa-create-menu__text">
              <strong>{t('createMenu.story')}</strong>
              <small>{t('createMenu.storyDescription')}</small>
            </span>
          </button>
          <button type="button" className="asa-create-menu__option" onClick={() => choose('/create/reel')}>
            <span className="asa-create-menu__icon" aria-hidden="true">
              🎬
            </span>
            <span className="asa-create-menu__text">
              <strong>{t('createMenu.reel')}</strong>
              <small>{t('createMenu.reelDescription')}</small>
            </span>
          </button>
        </div>
      </Modal>
    </>
  )
}

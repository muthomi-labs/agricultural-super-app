import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckIcon, XIcon } from '@/components/icons'
import { imageFileError, ALLOWED_IMAGE_MIME_TYPES } from '@/lib/imagePolicy'
import { uploadsService } from '@/services'
import { Spinner } from './Spinner'
import './ui.css'

let nextId = 0

/**
 * Real device file uploads (no more "paste an image URL"). Handles
 * selection, client-side validation, an instant local preview, the
 * actual upload with progress, and per-image error/remove -- the parent
 * only ever sees the list of confirmed server URLs via onChange.
 *
 * Deliberately omits the `capture` attribute on the file input: with
 * `accept="image/*"`-style MIME types but no `capture`, mobile browsers
 * show their native "Camera / Photos / Files" chooser, rather than being
 * locked to the camera only.
 */
export function ImageUploader({ label, value = [], onChange, onBusyChange, multiple = true, maxFiles = 6 }) {
  const { t } = useTranslation('common')
  const [items, setItems] = useState(() => value.map((url) => ({ id: `existing-${nextId++}`, url, previewUrl: url, status: 'done' })))
  const inputRef = useRef(null)
  const itemsRef = useRef(items)
  itemsRef.current = items

  useEffect(() => {
    // Revoke any locally-created object URLs on unmount to avoid leaking memory.
    return () => {
      itemsRef.current.forEach((item) => {
        if (item.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(item.previewUrl)
      })
    }
  }, [])

  // Notifying the parent belongs here, as a commit-phase effect -- NOT
  // inside a setItems updater function. An updater runs during React's
  // render phase, and calling a *different* component's setState from
  // there (onChange/onBusyChange update EditProfilePage/CreatePostPage's
  // state) is exactly what triggers React's "Cannot update a component
  // while rendering a different component" warning.
  useEffect(() => {
    onChange?.(items.filter((i) => i.status === 'done').map((i) => i.url))
    // Lets forms disable submit while a file is still mid-upload --
    // otherwise a submit that races an upload would silently publish
    // without that image, since only 'done' items are ever reported above.
    onBusyChange?.(items.some((i) => i.status === 'uploading'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items])

  function updateItem(id, patch) {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)))
  }

  function handleFiles(fileList) {
    const files = Array.from(fileList)
    const remainingSlots = maxFiles - items.length
    const toAdd = files.slice(0, Math.max(0, remainingSlots))

    const newItems = toAdd.map((file) => {
      const id = `new-${nextId++}`
      const error = imageFileError(file)
      if (error) {
        return { id, file, previewUrl: null, url: null, status: 'error', error, progress: 0 }
      }
      return { id, file, previewUrl: URL.createObjectURL(file), url: null, status: 'uploading', progress: 0 }
    })

    setItems((prev) => [...prev, ...newItems])

    newItems
      .filter((item) => item.status === 'uploading')
      .forEach((item) => {
        uploadsService
          .uploadImage(item.file, { onProgress: (progress) => updateItem(item.id, { progress }) })
          .then((result) => updateItem(item.id, { status: 'done', url: result.url }))
          .catch((err) => updateItem(item.id, { status: 'error', error: err?.message ?? t('imageUploader.uploadFailed') }))
      })
  }

  function handleRemove(id) {
    setItems((prev) => {
      const removed = prev.find((i) => i.id === id)
      if (removed?.previewUrl?.startsWith('blob:')) URL.revokeObjectURL(removed.previewUrl)
      return prev.filter((i) => i.id !== id)
    })
  }

  const canAddMore = items.length < maxFiles

  return (
    <div className="asa-field">
      {label && <span className="asa-field__label">{label}</span>}

      <div className="asa-image-uploader">
        {items.map((item) => (
          <div key={item.id} className={`asa-image-uploader__tile ${item.status === 'error' ? 'asa-image-uploader__tile--error' : ''}`}>
            {item.previewUrl ? (
              <img src={item.previewUrl} alt="" className="asa-image-uploader__img" />
            ) : (
              <div className="asa-image-uploader__placeholder" aria-hidden="true">
                <XIcon width={20} height={20} />
              </div>
            )}

            {item.status === 'uploading' && (
              <div className="asa-image-uploader__overlay">
                <Spinner size="sm" />
                <span>{item.progress}%</span>
              </div>
            )}

            {item.status === 'done' && (
              <span className="asa-image-uploader__badge asa-image-uploader__badge--done">
                <CheckIcon width={12} height={12} />
              </span>
            )}

            <button
              type="button"
              className="asa-image-uploader__remove"
              onClick={() => handleRemove(item.id)}
              aria-label={t('imageUploader.removeImage')}
            >
              <XIcon width={14} height={14} />
            </button>

            {item.status === 'error' && <span className="asa-image-uploader__error">{item.error}</span>}
          </div>
        ))}

        {canAddMore && (
          <button type="button" className="asa-image-uploader__add" onClick={() => inputRef.current?.click()}>
            <span className="asa-image-uploader__add-icon">+</span>
            <span>{multiple ? t('imageUploader.addPhotos') : t('imageUploader.choosePhoto')}</span>
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_IMAGE_MIME_TYPES.join(',')}
        multiple={multiple}
        className="visually-hidden"
        onChange={(e) => {
          if (e.target.files?.length) handleFiles(e.target.files)
          e.target.value = '' // allow re-selecting the same file later
        }}
      />

      <span className="asa-field__hint">{t('imageUploader.hint')}</span>
    </div>
  )
}

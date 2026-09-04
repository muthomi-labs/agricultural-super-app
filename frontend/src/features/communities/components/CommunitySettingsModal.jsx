import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Modal } from '@/components/ui'
import { errorMessage } from '@/features/auth/AuthContext'
import { updateCommunitySettings } from '@/store/slices/communitiesSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import '../communities.css'

const PERMISSION_VALUES = ['everyone', 'experts_only', 'admins_only']

export function CommunitySettingsModal({ open, onClose, community }) {
  const { t } = useTranslation('communities')
  const dispatch = useAppDispatch()
  const status = useAppSelector((state) => state.communities.settingsStatus)
  const [postingPermission, setPostingPermission] = useState(community.postingPermission)
  const [messagingPermission, setMessagingPermission] = useState(community.messagingPermission)
  const [commentsEnabled, setCommentsEnabled] = useState(community.commentsEnabled)
  const [error, setError] = useState(null)

  async function handleSave() {
    setError(null)
    try {
      await dispatch(
        updateCommunitySettings({
          communityId: community.id,
          settings: { postingPermission, messagingPermission, commentsEnabled },
        }),
      ).unwrap()
      onClose()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <Modal open={open} title={t('settings.title')} onClose={onClose}>
      <div className="asa-community-settings">
        <label className="asa-community-settings__field">
          <span>{t('settings.whoCanPost')}</span>
          <select value={postingPermission} onChange={(event) => setPostingPermission(event.target.value)}>
            {PERMISSION_VALUES.map((value) => (
              <option key={value} value={value}>
                {t(`detail.permissions.${value}`)}
              </option>
            ))}
          </select>
        </label>

        <label className="asa-community-settings__field">
          <span>{t('settings.whoCanComment')}</span>
          <select value={messagingPermission} onChange={(event) => setMessagingPermission(event.target.value)}>
            {PERMISSION_VALUES.map((value) => (
              <option key={value} value={value}>
                {t(`detail.permissions.${value}`)}
              </option>
            ))}
          </select>
        </label>

        <label className="asa-community-settings__checkbox">
          <input
            type="checkbox"
            checked={commentsEnabled}
            onChange={(event) => setCommentsEnabled(event.target.checked)}
          />
          <span>{t('settings.allowComments')}</span>
        </label>

        {error && (
          <p className="asa-form-error" role="alert">
            {error}
          </p>
        )}

        <Button onClick={handleSave} loading={status === 'loading'}>
          {t('settings.save')}
        </Button>
      </div>
    </Modal>
  )
}

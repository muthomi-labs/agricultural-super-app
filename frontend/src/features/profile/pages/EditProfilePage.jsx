import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, ImageUploader, Input, LanguageSwitcher, PageHeader, Textarea } from '@/components/ui'
import { updateProfile } from '@/store/slices/profileSlice'
import { useAppDispatch } from '@/store/hooks'
import { useAuth, errorMessage } from '@/features/auth/AuthContext'

export function EditProfilePage() {
  const { t } = useTranslation('profile')
  const { user, refreshProfile } = useAuth()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const [form, setForm] = useState({
    firstName: user?.profile.firstName ?? '',
    lastName: user?.profile.lastName ?? '',
    bio: user?.profile.bio ?? '',
    location: user?.profile.location ?? '',
    phoneNumber: user?.profile.phoneNumber ?? '',
  })
  const [profileImageUrl, setProfileImageUrl] = useState(user?.profile.profileImageUrl ?? null)
  const [imageUploading, setImageUploading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!user || saving || imageUploading) return
    setSaving(true)
    setError(null)
    try {
      const updated = await dispatch(
        updateProfile({
          userId: user.user.id,
          input: {
            firstName: form.firstName.trim() || null,
            lastName: form.lastName.trim() || null,
            bio: form.bio.trim() || null,
            location: form.location.trim() || null,
            phoneNumber: form.phoneNumber.trim() || null,
            profileImageUrl: profileImageUrl || null,
          },
        }),
      ).unwrap()
      refreshProfile(updated)
      navigate('/profile', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title={t('edit.title')} subtitle={t('edit.subtitle')} />
      <form onSubmit={handleSubmit}>
        <ImageUploader
          label={t('edit.photo')}
          multiple={false}
          maxFiles={1}
          value={profileImageUrl ? [profileImageUrl] : []}
          onChange={(urls) => setProfileImageUrl(urls[0] ?? null)}
          onBusyChange={setImageUploading}
        />
        <Input
          label={t('edit.firstName')}
          name="firstName"
          autoComplete="given-name"
          value={form.firstName}
          onChange={(e) => setField('firstName', e.target.value)}
        />
        <Input
          label={t('edit.lastName')}
          name="lastName"
          autoComplete="family-name"
          value={form.lastName}
          onChange={(e) => setField('lastName', e.target.value)}
        />
        <Textarea
          label={t('edit.bio')}
          name="bio"
          rows={4}
          value={form.bio}
          onChange={(e) => setField('bio', e.target.value)}
        />
        <Input
          label={t('edit.location')}
          name="location"
          value={form.location}
          onChange={(e) => setField('location', e.target.value)}
          placeholder={t('edit.locationPlaceholder')}
        />
        <Input
          label={t('edit.phoneNumber')}
          name="phoneNumber"
          type="tel"
          autoComplete="tel"
          value={form.phoneNumber}
          onChange={(e) => setField('phoneNumber', e.target.value)}
        />
        <div className="asa-field">
          <span className="asa-field__label">{t('edit.language')}</span>
          <span className="asa-field__hint">{t('edit.languageDescription')}</span>
          <LanguageSwitcher />
        </div>
        {error && (
          <p className="asa-form-error" role="alert">
            {error}
          </p>
        )}
        <div className="asa-profile-edit__actions">
          <Button type="submit" loading={saving} disabled={saving || imageUploading}>
            {imageUploading ? t('edit.waitingForPhoto') : t('edit.saveChanges')}
          </Button>
          <Button variant="ghost" type="button" onClick={() => navigate('/profile')}>
            {t('edit.cancel')}
          </Button>
        </div>
      </form>
    </>
  )
}
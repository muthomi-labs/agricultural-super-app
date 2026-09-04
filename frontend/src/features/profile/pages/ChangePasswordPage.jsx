import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, PageHeader, PasswordInput, PasswordRequirements } from '@/components/ui'
import { useAuth, errorMessage } from '@/features/auth/AuthContext'
import { isPasswordStrong } from '@/lib/passwordPolicy'

export function ChangePasswordPage() {
  const { t } = useTranslation('auth')
  const { changePassword } = useAuth()
  const navigate = useNavigate()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  function validate() {
    const errors = {}
    if (!currentPassword) errors.currentPassword = t('changePassword.errors.currentPasswordRequired')
    if (!newPassword) errors.newPassword = t('changePassword.errors.newPasswordRequired')
    else if (!isPasswordStrong(newPassword)) errors.newPassword = t('changePassword.errors.passwordWeak')
    if (confirmPassword !== newPassword) errors.confirmPassword = t('changePassword.errors.confirmPasswordMismatch')
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!validate() || submitting) return
    setSubmitting(true)
    setFormError(null)
    try {
      await changePassword(currentPassword, newPassword)
      setDone(true)
    } catch (error) {
      setFormError(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <>
        <PageHeader title={t('changePassword.doneTitle')} subtitle={t('changePassword.doneSubtitle')} />
        <Button onClick={() => navigate('/profile')}>{t('changePassword.backToProfile')}</Button>
      </>
    )
  }

  return (
    <>
      <PageHeader title={t('changePassword.title')} subtitle={t('changePassword.subtitle')} />
      <form onSubmit={handleSubmit} noValidate>
        <PasswordInput
          label={t('changePassword.currentPassword')}
          name="currentPassword"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          error={fieldErrors.currentPassword}
        />
        <PasswordInput
          label={t('changePassword.newPassword')}
          name="newPassword"
          autoComplete="new-password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          error={fieldErrors.newPassword}
        />
        <PasswordRequirements password={newPassword} />
        <PasswordInput
          label={t('changePassword.confirmNewPassword')}
          name="confirmPassword"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          error={fieldErrors.confirmPassword}
        />
        {formError && (
          <p className="asa-form-error" role="alert">
            {formError}
          </p>
        )}
        <div className="asa-profile-edit__actions">
          <Button type="submit" loading={submitting} disabled={submitting || !isPasswordStrong(newPassword)}>
            {t('changePassword.submit')}
          </Button>
          <Button variant="ghost" type="button" onClick={() => navigate('/profile')}>
            {t('changePassword.cancel')}
          </Button>
        </div>
      </form>
    </>
  )
}

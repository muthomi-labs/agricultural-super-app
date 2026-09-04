import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, PasswordInput, PasswordRequirements } from '@/components/ui'
import { useAuth, errorMessage } from '@/features/auth/AuthContext'
import { isPasswordStrong } from '@/lib/passwordPolicy'
import { AuthLayout } from './AuthLayout'
import './auth.css'

export function ResetPasswordPage() {
  const { t } = useTranslation('auth')
  const { resetPassword } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  function validate() {
    const errors = {}
    if (!password) errors.password = t('resetPassword.errors.passwordRequired')
    else if (!isPasswordStrong(password)) errors.password = t('resetPassword.errors.passwordWeak')
    if (confirmPassword !== password) errors.confirmPassword = t('resetPassword.errors.confirmPasswordMismatch')
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!validate() || submitting) return
    setSubmitting(true)
    setFormError(null)
    try {
      await resetPassword(token, password)
      setDone(true)
    } catch (error) {
      setFormError(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  if (!token) {
    return (
      <AuthLayout
        title={t('resetPassword.invalidLinkTitle')}
        subtitle={t('resetPassword.invalidLinkSubtitle')}
        footer={
          <>
            <Link to="/forgot-password">{t('resetPassword.requestNewLink')}</Link>
          </>
        }
      >
        <p className="asa-auth__hint">{t('resetPassword.invalidLinkHint')}</p>
      </AuthLayout>
    )
  }

  if (done) {
    return (
      <AuthLayout title={t('resetPassword.doneTitle')} subtitle={t('resetPassword.doneSubtitle')}>
        <Button block onClick={() => navigate('/login', { replace: true })}>
          {t('resetPassword.logIn')}
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title={t('resetPassword.title')} subtitle={t('resetPassword.subtitle')}>
      <form onSubmit={handleSubmit} noValidate>
        <PasswordInput
          label={t('resetPassword.newPassword')}
          name="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
        />
        <PasswordRequirements password={password} />
        <PasswordInput
          label={t('resetPassword.confirmNewPassword')}
          name="confirmPassword"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          error={fieldErrors.confirmPassword}
        />
        {formError && (
          <p className="asa-auth__error" role="alert">
            {formError}
          </p>
        )}
        <Button type="submit" block loading={submitting} disabled={submitting || !isPasswordStrong(password)}>
          {t('resetPassword.submit')}
        </Button>
      </form>
    </AuthLayout>
  )
}

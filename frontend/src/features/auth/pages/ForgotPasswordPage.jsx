import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, Input } from '@/components/ui'
import { useAuth, errorMessage } from '@/features/auth/AuthContext'
import { AuthLayout } from './AuthLayout'
import './auth.css'

export function ForgotPasswordPage() {
  const { t } = useTranslation('auth')
  const { forgotPassword } = useAuth()

  const [email, setEmail] = useState('')
  const [fieldError, setFieldError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return
    if (!email.trim()) {
      setFieldError(t('forgotPassword.errors.emailRequired'))
      return
    }
    setFieldError(null)
    setFormError(null)
    setSubmitting(true)
    try {
      await forgotPassword(email.trim())
      setSent(true)
    } catch (error) {
      setFormError(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  if (sent) {
    return (
      <AuthLayout
        title={t('forgotPassword.checkEmailTitle')}
        subtitle={t('forgotPassword.checkEmailSubtitle')}
        footer={
          <>
            {t('forgotPassword.rememberedIt')} <Link to="/login">{t('forgotPassword.backToLogin')}</Link>
          </>
        }
      >
        <p className="asa-auth__hint">
          {t('forgotPassword.hint')}{' '}
          <button type="button" className="asa-auth__linklike" onClick={() => setSent(false)}>
            {t('forgotPassword.tryAgain')}
          </button>
          .
        </p>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title={t('forgotPassword.title')}
      subtitle={t('forgotPassword.subtitle')}
      footer={
        <>
          {t('forgotPassword.rememberedIt')} <Link to="/login">{t('forgotPassword.backToLogin')}</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        <Input
          label={t('forgotPassword.email')}
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldError}
          placeholder="you@example.com"
        />
        {formError && (
          <p className="asa-auth__error" role="alert">
            {formError}
          </p>
        )}
        <Button type="submit" block loading={submitting}>
          {t('forgotPassword.submit')}
        </Button>
      </form>
    </AuthLayout>
  )
}

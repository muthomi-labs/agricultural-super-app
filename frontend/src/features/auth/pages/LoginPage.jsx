import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, Input, PasswordInput } from '@/components/ui'
import { useAuth, errorMessage } from '@/features/auth/AuthContext'
import { AuthLayout } from './AuthLayout'
import './auth.css'

export function LoginPage() {
  const { t } = useTranslation('auth')
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [usernameOrEmail, setUsernameOrEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const from = location.state?.from ?? '/'

  function validate() {
    const errors = {}
    if (!usernameOrEmail.trim()) errors.usernameOrEmail = t('login.errors.usernameOrEmailRequired')
    if (!password) errors.password = t('login.errors.passwordRequired')
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!validate() || submitting) return
    setSubmitting(true)
    setFormError(null)
    try {
      await login(usernameOrEmail.trim(), password)
      navigate(from, { replace: true })
    } catch (error) {
      setFormError(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title={t('login.title')}
      subtitle={t('login.subtitle')}
      footer={
        <>
          {t('login.newHere')} <Link to="/register">{t('login.createAccount')}</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        <Input
          label={t('login.usernameOrEmail')}
          name="usernameOrEmail"
          type="text"
          autoComplete="username"
          value={usernameOrEmail}
          onChange={(e) => setUsernameOrEmail(e.target.value)}
          error={fieldErrors.usernameOrEmail}
          placeholder={t('login.usernameOrEmailPlaceholder')}
        />
        <PasswordInput
          label={t('login.password')}
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
          placeholder={t('login.passwordPlaceholder')}
        />
        <Link to="/forgot-password" className="asa-auth__forgot">
          {t('login.forgotPassword')}
        </Link>
        {formError && (
          <p className="asa-auth__error" role="alert">
            {formError}
          </p>
        )}
        <Button type="submit" block loading={submitting}>
          {t('login.submit')}
        </Button>
      </form>
    </AuthLayout>
  )
}
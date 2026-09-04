import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, Input, PasswordInput, PasswordRequirements } from '@/components/ui'
import { useAuth, errorMessage } from '@/features/auth/AuthContext'
import { isPasswordStrong } from '@/lib/passwordPolicy'
import { AuthLayout } from './AuthLayout'
import './auth.css'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function RegisterPage() {
  const { t, i18n } = useTranslation('auth')
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
  })
  const [passwordTouched, setPasswordTouched] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }))
    setFieldErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  function validate() {
    const errors = {}
    if (!form.username.trim()) errors.username = t('register.errors.usernameRequired')
    if (form.username.trim().length < 3) errors.username = t('register.errors.usernameTooShort')
    if (!form.email.trim()) errors.email = t('register.errors.emailRequired')
    else if (!EMAIL_PATTERN.test(form.email.trim())) errors.email = t('register.errors.emailInvalid')
    if (!form.password) errors.password = t('register.errors.passwordRequired')
    else if (!isPasswordStrong(form.password)) errors.password = t('register.errors.passwordWeak')
    if (form.confirmPassword !== form.password) errors.confirmPassword = t('register.errors.confirmPasswordMismatch')
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setPasswordTouched(true)
    if (!validate() || submitting) return
    setSubmitting(true)
    setFormError(null)
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        // Whatever language the visitor was using to fill out this form
        // (see AuthLayout's LanguageSwitcher) becomes the new account's
        // saved preference, rather than every account silently starting
        // on English regardless of how they got here.
        language: i18n.language?.startsWith('sw') ? 'sw' : 'en',
        firstName: form.firstName.trim() || undefined,
        lastName: form.lastName.trim() || undefined,
      })
      navigate('/', { replace: true })
    } catch (error) {
      setFormError(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title={t('register.title')}
      subtitle={t('register.subtitle')}
      footer={
        <>
          {t('register.alreadyHaveAccount')} <Link to="/login">{t('register.logIn')}</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        <Input
          label={t('register.username')}
          name="username"
          autoComplete="username"
          value={form.username}
          onChange={(e) => setField('username', e.target.value)}
          error={fieldErrors.username}
          placeholder={t('register.usernamePlaceholder')}
        />
        <Input
          label={t('register.email')}
          name="email"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={(e) => setField('email', e.target.value)}
          error={fieldErrors.email}
          placeholder={t('register.emailPlaceholder')}
        />
        <PasswordInput
          label={t('register.password')}
          name="password"
          autoComplete="new-password"
          value={form.password}
          onChange={(e) => setField('password', e.target.value)}
          onFocus={() => setPasswordTouched(true)}
          error={fieldErrors.password}
        />
        {(passwordTouched || form.password) && <PasswordRequirements password={form.password} />}
        <PasswordInput
          label={t('register.confirmPassword')}
          name="confirmPassword"
          autoComplete="new-password"
          value={form.confirmPassword}
          onChange={(e) => setField('confirmPassword', e.target.value)}
          error={fieldErrors.confirmPassword}
        />
        <Input
          label={t('register.firstName')}
          name="firstName"
          autoComplete="given-name"
          value={form.firstName}
          onChange={(e) => setField('firstName', e.target.value)}
          error={fieldErrors.firstName}
        />
        <Input
          label={t('register.lastName')}
          name="lastName"
          autoComplete="family-name"
          value={form.lastName}
          onChange={(e) => setField('lastName', e.target.value)}
          error={fieldErrors.lastName}
        />
        {formError && (
          <p className="asa-auth__error" role="alert">
            {formError}
          </p>
        )}
        <Button type="submit" block loading={submitting} disabled={submitting || !isPasswordStrong(form.password)}>
          {t('register.submit')}
        </Button>
      </form>
    </AuthLayout>
  )
}

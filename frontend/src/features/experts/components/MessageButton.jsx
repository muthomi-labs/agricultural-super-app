import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui'
import { errorMessage } from '@/features/auth/AuthContext'
import { useAppDispatch } from '@/store/hooks'
import { startConversationWithUser } from '@/store/slices/messagesSlice'

export function MessageButton({ userId, variant = 'secondary', size = 'sm' }) {
  const { t } = useTranslation('experts')
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleClick() {
    if (loading) return
    setLoading(true)
    setError(null)
    try {
      const conversation = await dispatch(startConversationWithUser(userId)).unwrap()
      navigate(`/messages/${conversation.id}`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <span>
      <Button variant={variant} size={size} onClick={handleClick} loading={loading}>
        {t('message.message')}
      </Button>
      {error && (
        <p className="asa-form-error" role="alert">
          {error}
        </p>
      )}
    </span>
  )
}

import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { formatRelativeTime } from '@/lib/format'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { createAIConversation, deleteAIConversation, fetchAIConversations } from '@/store/slices/aiSlice'
import '../assistant.css'

export function AiAssistantPage() {
  const { t } = useTranslation('assistant')
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const conversations = useAppSelector((state) => state.ai.conversations)
  const status = useAppSelector((state) => state.ai.conversationsStatus)
  const error = useAppSelector((state) => state.ai.conversationsError)

  useEffect(() => {
    dispatch(fetchAIConversations())
  }, [dispatch])

  async function handleNewConversation() {
    const result = await dispatch(createAIConversation())
    if (createAIConversation.fulfilled.match(result)) {
      navigate(`/assistant/${result.payload.id}`)
    }
  }

  function handleDelete(event, conversationId) {
    event.stopPropagation()
    if (!window.confirm(t('page.confirmDelete'))) return
    dispatch(deleteAIConversation(conversationId))
  }

  return (
    <>
      <PageHeader
        title={t('page.title')}
        subtitle={t('page.subtitle')}
        actions={<Button onClick={handleNewConversation}>{t('page.newConversation')}</Button>}
      />

      <p className="asa-assistant__disclaimer">{t('page.disclaimer')}</p>

      {status === 'loading' && <LoadingState label={t('page.loading')} />}
      {status === 'error' && (
        <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchAIConversations())} />
      )}
      {status === 'ready' && conversations.length === 0 && (
        <EmptyState
          title={t('page.emptyTitle')}
          description={t('page.emptyDescription')}
          icon="🌾"
          action={<Button onClick={handleNewConversation}>{t('page.startFirst')}</Button>}
        />
      )}
      {status === 'ready' && conversations.length > 0 && (
        <ul className="asa-ai-conversation-list">
          {conversations.map((conversation) => (
            <li key={conversation.id} className="asa-ai-conversation-row">
              <button
                type="button"
                className="asa-ai-conversation-item"
                onClick={() => navigate(`/assistant/${conversation.id}`)}
              >
                <span className="asa-ai-conversation-item__name">
                  {conversation.title ?? t('page.newConversationFallback')}
                </span>
                <span className="asa-ai-conversation-item__time">{formatRelativeTime(conversation.updatedAt)}</span>
              </button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(event) => handleDelete(event, conversation.id)}
                aria-label={t('page.deleteConversation')}
              >
                {t('page.delete')}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

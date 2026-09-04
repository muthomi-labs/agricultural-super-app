import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { formatRelativeTime } from '@/lib/format'
import { useAuth } from '@/features/auth/AuthContext'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { fetchConversations } from '@/store/slices/messagesSlice'
import '../messaging.css'

function otherParticipants(conversation, myId) {
  return conversation.participants.filter((p) => p.userId !== myId).map((p) => p.participant)
}

function lastMessage(conversation) {
  if (conversation.messages.length === 0) return null
  return [...conversation.messages].sort((a, b) => a.createdAt.localeCompare(b.createdAt)).at(-1)
}

function unreadCount(conversation, myId) {
  return conversation.messages.filter((m) => m.senderId !== myId && !m.isRead).length
}

export function MessagesPage() {
  const { t } = useTranslation('messaging')
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { user } = useAuth()
  const conversations = useAppSelector((state) => state.messages.conversations)
  const status = useAppSelector((state) => state.messages.conversationsStatus)
  const error = useAppSelector((state) => state.messages.conversationsError)

  useEffect(() => {
    dispatch(fetchConversations())
  }, [dispatch])

  const myId = user?.user.id

  return (
    <>
      <PageHeader title={t('list.title')} subtitle={t('list.subtitle')} />

      {status === 'loading' && <LoadingState label={t('list.loading')} />}
      {status === 'error' && <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchConversations())} />}
      {status === 'ready' && conversations.length === 0 && (
        <EmptyState
          title={t('list.emptyTitle')}
          description={t('list.emptyDescription')}
          icon="💬"
        />
      )}
      {status === 'ready' && conversations.length > 0 && (
        <ul className="asa-conversation-list">
          {conversations.map((conversation) => {
            const [partner] = otherParticipants(conversation, myId)
            const name =
              partner?.profile.firstName && partner?.profile.lastName
                ? `${partner.profile.firstName} ${partner.profile.lastName}`
                : partner?.user.username ?? t('list.conversationFallback')
            const last = lastMessage(conversation)
            const unread = unreadCount(conversation, myId)

            return (
              <li key={conversation.id}>
                <button
                  type="button"
                  className="asa-conversation-item"
                  onClick={() => navigate(`/messages/${conversation.id}`)}
                >
                  <Avatar imageUrl={partner?.profile.profileImageUrl} name={name} username={partner?.user.username} size="lg" />
                  <div className="asa-conversation-item__body">
                    <div className="asa-conversation-item__top">
                      <span className={`asa-conversation-item__name ${unread > 0 ? 'asa-conversation-item__name--unread' : ''}`}>
                        {name}
                      </span>
                      {last && <span className="asa-conversation-item__time">{formatRelativeTime(last.createdAt)}</span>}
                    </div>
                    <p className={`asa-conversation-item__preview ${unread > 0 ? 'asa-conversation-item__preview--unread' : ''}`}>
                      {last
                        ? last.senderId === myId
                          ? t('list.youPrefix', { content: last.content })
                          : last.content
                        : t('list.noMessagesYet')}
                    </p>
                  </div>
                  {unread > 0 && <span className="asa-unread-dot">{unread}</span>}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </>
  )
}

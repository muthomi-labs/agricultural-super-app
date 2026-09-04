import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Button, ErrorState, LoadingState, Textarea } from '@/components/ui'
import { SendIcon } from '@/components/icons'
import { formatRelativeTime } from '@/lib/format'
import { useAuth } from '@/features/auth/AuthContext'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { fetchConversation, markMessageRead, sendMessage } from '@/store/slices/messagesSlice'
import '../messaging.css'

export function ConversationPage() {
  const { t } = useTranslation('messaging')
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { user } = useAuth()

  const conversation = useAppSelector((state) => state.messages.current)
  const status = useAppSelector((state) => state.messages.currentStatus)
  const error = useAppSelector((state) => state.messages.currentError)
  const sending = useAppSelector((state) => state.messages.sending)

  const [draft, setDraft] = useState('')
  const bottomRef = useRef(null)
  const myId = user?.user.id

  useEffect(() => {
    if (conversationId) dispatch(fetchConversation(Number(conversationId)))
  }, [dispatch, conversationId])

  useEffect(() => {
    if (!conversation || conversation.id !== Number(conversationId)) return
    conversation.messages
      .filter((m) => m.senderId !== myId && !m.isRead)
      .forEach((m) => dispatch(markMessageRead(m.id)))
  }, [conversation, conversationId, myId, dispatch])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [conversation?.messages.length])

  if (status === 'loading') return <LoadingState label={t('thread.loading')} />
  if (status === 'error' || !conversation) {
    return <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchConversation(Number(conversationId)))} />
  }

  const partner = conversation.participants.find((p) => p.userId !== myId)?.participant
  const partnerName =
    partner?.profile.firstName && partner?.profile.lastName
      ? `${partner.profile.firstName} ${partner.profile.lastName}`
      : partner?.user.username ?? t('list.conversationFallback')

  const orderedMessages = [...conversation.messages].sort((a, b) => a.createdAt.localeCompare(b.createdAt))

  function handleSend(event) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || sending) return
    dispatch(sendMessage({ conversationId: conversation.id, content }))
    setDraft('')
  }

  return (
    <div className="asa-thread">
      <header className="asa-thread__header">
        <Button variant="ghost" size="sm" onClick={() => navigate('/messages')} aria-label={t('thread.backToMessages')}>
          &larr;
        </Button>
        <Avatar imageUrl={partner?.profile.profileImageUrl} name={partnerName} username={partner?.user.username} size="sm" />
        <strong>{partnerName}</strong>
      </header>

      <div className="asa-thread__messages">
        {orderedMessages.map((message) => {
          const mine = message.senderId === myId
          return (
            <div key={message.id} className={`asa-thread-message ${mine ? 'asa-thread-message--mine' : ''}`}>
              <div className="asa-thread-message__bubble">
                {message.content}
                <span className="asa-thread-message__time">{formatRelativeTime(message.createdAt)}</span>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      <form className="asa-thread__composer" onSubmit={handleSend}>
        <Textarea
          label=""
          name="draft"
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={t('thread.placeholder')}
          aria-label={t('thread.ariaLabel')}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend(e)
            }
          }}
        />
        <Button type="submit" loading={sending} disabled={!draft.trim()} aria-label={t('thread.send')}>
          <SendIcon width={18} height={18} />
        </Button>
      </form>
    </div>
  )
}

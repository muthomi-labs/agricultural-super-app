import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Button, PostContent, Spinner, Textarea } from '@/components/ui'
import { BotIcon, XIcon } from '@/components/icons'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import {
  clearAISendError,
  createAIConversation,
  fetchAIConversation,
  fetchAIConversations,
  streamAIMessage,
} from '@/store/slices/aiSlice'
import '../assistant.css'

export function FloatingAssistant() {
  const location = useLocation()
  const dispatch = useAppDispatch()

  const [open, setOpen] = useState(false)
  const [view, setView] = useState('list')
  const [draft, setDraft] = useState('')
  const [lastFailedContent, setLastFailedContent] = useState(null)
  const bottomRef = useRef(null)
  const pendingContentRef = useRef(null)

  const conversations = useAppSelector((state) => state.ai.conversations)
  const conversationsStatus = useAppSelector((state) => state.ai.conversationsStatus)
  const current = useAppSelector((state) => state.ai.current)
  const currentStatus = useAppSelector((state) => state.ai.currentStatus)
  const sending = useAppSelector((state) => state.ai.sending)
  const sendError = useAppSelector((state) => state.ai.sendError)
  const streamingReply = useAppSelector((state) => state.ai.streamingReply)

  useEffect(() => {
    if (open) dispatch(fetchAIConversations())
  }, [dispatch, open])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [current?.messages.length, streamingReply?.content, view])

  useEffect(() => {
    if (sendError) setLastFailedContent(pendingContentRef.current)
  }, [sendError])

  function send(text) {
    const content = text.trim()
    if (!content || sending || !current) return
    setDraft('')
    setLastFailedContent(null)
    dispatch(clearAISendError())
    pendingContentRef.current = content
    dispatch(streamAIMessage({ conversationId: current.id, content }))
  }

  async function startNewConversation() {
    const result = await dispatch(createAIConversation())
    if (createAIConversation.fulfilled.match(result)) setView('chat')
  }

  function openConversation(conversationId) {
    dispatch(fetchAIConversation(conversationId))
    setView('chat')
  }

  function handleSubmit(event) {
    event.preventDefault()
    send(draft)
  }

  if (location.pathname.startsWith('/assistant')) return null

  if (!open) {
    return (
      <button
        type="button"
        className="asa-floating-ai__trigger"
        onClick={() => setOpen(true)}
        aria-label="Open AI assistant"
      >
        <BotIcon width={20} height={20} />
        <span>AI</span>
      </button>
    )
  }

  return (
    <div className="asa-floating-ai__panel" role="dialog" aria-label="Agricultural AI assistant">
      <header className="asa-floating-ai__header">
        {view === 'chat' ? (
          <button
            type="button"
            className="asa-floating-ai__icon-btn"
            onClick={() => setView('list')}
            aria-label="Back to conversations"
          >
            &larr;
          </button>
        ) : (
          <BotIcon width={18} height={18} />
        )}
        <strong className="asa-floating-ai__title">Agricultural AI</strong>
        <button
          type="button"
          className="asa-floating-ai__icon-btn"
          onClick={() => setOpen(false)}
          aria-label="Close AI assistant"
        >
          <XIcon width={16} height={16} />
        </button>
      </header>

      {view === 'list' && (
        <div className="asa-floating-ai__list">
          <Button size="sm" onClick={startNewConversation}>
            New conversation
          </Button>

          {conversationsStatus === 'loading' && <Spinner size="sm" />}
          {conversationsStatus === 'ready' && conversations.length === 0 && (
            <p className="asa-floating-ai__empty">Ask about crops, pests, soil, livestock, and more.</p>
          )}

          <ul className="asa-floating-ai__conversations">
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <button type="button" onClick={() => openConversation(conversation.id)}>
                  {conversation.title ?? 'New conversation'}
                </button>
              </li>
            ))}
          </ul>

          <Link to="/assistant" className="asa-floating-ai__full-link" onClick={() => setOpen(false)}>
            Open full assistant
          </Link>
        </div>
      )}

      {view === 'chat' && (
        <>
          <div className="asa-floating-ai__messages">
            {currentStatus === 'loading' && <Spinner size="sm" />}
            {current?.messages.map((message) => (
              <div key={message.id} className={`asa-floating-ai-message asa-floating-ai-message--${message.role}`}>
                {message.role === 'assistant' ? <PostContent content={message.content} /> : message.content}
              </div>
            ))}
            {streamingReply && (
              <div className="asa-floating-ai-message asa-floating-ai-message--assistant">
                {streamingReply.content ? <PostContent content={streamingReply.content} /> : <Spinner size="sm" />}
              </div>
            )}
            {sendError && (
              <div className="asa-floating-ai-message asa-floating-ai-message--error">
                {sendError}
                <Button variant="outline" size="sm" onClick={() => lastFailedContent && send(lastFailedContent)}>
                  Try again
                </Button>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form className="asa-floating-ai__composer" onSubmit={handleSubmit}>
            <Textarea
              label=""
              name="floating-ai-draft"
              rows={1}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask anything…"
              aria-label="Ask the assistant"
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  handleSubmit(event)
                }
              }}
            />
            <Button type="submit" size="sm" loading={sending} disabled={!draft.trim()} aria-label="Send">
              ➤
            </Button>
          </form>
        </>
      )}
    </div>
  )
}

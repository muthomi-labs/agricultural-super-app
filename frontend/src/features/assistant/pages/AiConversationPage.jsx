import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, ErrorState, LoadingState, PostContent, Spinner, Textarea } from '@/components/ui'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { clearAISendError, fetchAIConversation, streamAIMessage } from '@/store/slices/aiSlice'
import '../assistant.css'

export function AiConversationPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()

  const conversation = useAppSelector((state) => state.ai.current)
  const status = useAppSelector((state) => state.ai.currentStatus)
  const error = useAppSelector((state) => state.ai.currentError)
  const sending = useAppSelector((state) => state.ai.sending)
  const sendError = useAppSelector((state) => state.ai.sendError)
  const streamingReply = useAppSelector((state) => state.ai.streamingReply)

  const [draft, setDraft] = useState('')
  const [lastFailedContent, setLastFailedContent] = useState(null)
  const bottomRef = useRef(null)
  const pendingContentRef = useRef(null)

  useEffect(() => {
    if (conversationId) dispatch(fetchAIConversation(Number(conversationId)))
  }, [dispatch, conversationId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [conversation?.messages.length, streamingReply?.content])

  // streamAIMessage always resolves (a failure mid-stream is reported via
  // the aiStreamFailed action, not a rejected promise), so the retry
  // target is captured in a ref when a send starts and only surfaced once
  // sendError actually shows up.
  useEffect(() => {
    if (sendError) setLastFailedContent(pendingContentRef.current)
  }, [sendError])

  function send(text) {
    const content = text.trim()
    if (!content || sending) return
    setDraft('')
    setLastFailedContent(null)
    dispatch(clearAISendError())
    pendingContentRef.current = content
    dispatch(streamAIMessage({ conversationId: Number(conversationId), content }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    send(draft)
  }

  function retry() {
    if (lastFailedContent) send(lastFailedContent)
  }

  if (status === 'loading') return <LoadingState label="Loading conversation…" />
  if (status === 'error' || !conversation) {
    return (
      <ErrorState
        message={error ?? undefined}
        onRetry={() => dispatch(fetchAIConversation(Number(conversationId)))}
      />
    )
  }

  return (
    <div className="asa-assistant">
      <div className="asa-assistant__header">
        <Button variant="ghost" size="sm" onClick={() => navigate('/assistant')} aria-label="Back to conversations">
          &larr;
        </Button>
        <strong>{conversation.title ?? 'New conversation'}</strong>
      </div>

      <p className="asa-assistant__disclaimer">
        AI-generated guidance for quick, general advice. For anything high-stakes — disease outbreaks, chemical
        dosing, big financial decisions — confirm with a verified expert on AgriConnect.
      </p>

      <div className="asa-assistant__messages">
        {conversation.messages.map((message) => (
          <div key={message.id} className={`asa-assistant-message asa-assistant-message--${message.role}`}>
            <div className="asa-assistant-message__bubble">
              {message.role === 'assistant' ? (
                <PostContent content={message.content} />
              ) : (
                message.content
              )}
            </div>
          </div>
        ))}

        {streamingReply && (
          <div className="asa-assistant-message asa-assistant-message--assistant">
            <div className="asa-assistant-message__bubble">
              {streamingReply.content ? <PostContent content={streamingReply.content} /> : <Spinner size="sm" />}
            </div>
          </div>
        )}

        {sendError && (
          <div className="asa-assistant-message asa-assistant-message--error">
            <div className="asa-assistant-message__bubble">
              {sendError}
              <div style={{ marginTop: 'var(--space-2)' }}>
                <Button variant="outline" size="sm" onClick={retry}>
                  Try again
                </Button>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form className="asa-assistant__composer" onSubmit={handleSubmit}>
        <Textarea
          label=""
          name="draft"
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask a farming question…"
          aria-label="Your question"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
        />
        <Button type="submit" loading={sending} disabled={!draft.trim()}>
          Ask
        </Button>
      </form>
    </div>
  )
}

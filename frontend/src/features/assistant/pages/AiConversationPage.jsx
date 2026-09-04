import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button, ErrorState, LoadingState, PostContent, Spinner, Textarea } from '@/components/ui'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { cancelAIStream, clearAISendError, fetchAIConversation, streamAIMessage } from '@/store/slices/aiSlice'
import { looksKiswahili } from '@/lib/language'
import { aiService } from '@/services'
import '../assistant.css'

function translationPrompt(content, targetLanguage) {
  const instruction =
    targetLanguage === 'sw'
      ? 'Translate the following agricultural guidance into natural, professional Kiswahili, using correct Kenyan agricultural terminology. Keep any usernames, numbers, dates, emojis, and links unchanged. Reply with only the translation, no commentary.'
      : 'Translate the following agricultural guidance into natural, professional English, preserving agricultural terminology precisely. Keep any usernames, numbers, dates, emojis, and links unchanged. Reply with only the translation, no commentary.'
  return `${instruction}\n\n${content}`
}

/**
 * "Translate to Kiswahili" / "Translate to English" action on one
 * assistant reply. Deliberately reuses the existing stateless
 * /api/ai/assistant endpoint (aiService.askAssistant) rather than a
 * separate translation system -- see ai_service.py's _build_system_prompt
 * for the backend half of Kiswahili support. Hidden when the reply
 * already looks like it's in the target language (looksKiswahili), per
 * "don't unnecessarily translate it again."
 */
function AssistantBubble({ content }) {
  const { t } = useTranslation('assistant')
  const [translated, setTranslated] = useState(null)
  const [translating, setTranslating] = useState(false)

  const alreadyKiswahili = looksKiswahili(content)
  const targetLanguage = alreadyKiswahili ? 'en' : 'sw'
  const actionLabel = alreadyKiswahili ? t('conversation.translateToEnglish') : t('conversation.translateToKiswahili')

  async function handleTranslate() {
    if (translating) return
    setTranslating(true)
    try {
      const reply = await aiService.askAssistant([
        { role: 'user', content: translationPrompt(content, targetLanguage) },
      ])
      setTranslated(reply)
    } catch {
      // Best-effort UI affordance -- if it fails, the original content is
      // still fully readable, so this stays silent rather than showing a
      // blocking error for a non-critical action.
    } finally {
      setTranslating(false)
    }
  }

  return (
    <>
      <PostContent content={translated ?? content} />
      <div className="asa-assistant-message__translate">
        {translated ? (
          <span className="asa-assistant-message__translated-tag">{t('conversation.translated')}</span>
        ) : (
          <button type="button" className="asa-assistant-message__translate-btn" onClick={handleTranslate} disabled={translating}>
            {translating ? t('conversation.translating') : actionLabel}
          </button>
        )}
      </div>
    </>
  )
}

export function AiConversationPage() {
  const { t } = useTranslation('assistant')
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

  if (status === 'loading') return <LoadingState label={t('conversation.loading')} />
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
        <Button variant="ghost" size="sm" onClick={() => navigate('/assistant')} aria-label={t('conversation.backToConversations')}>
          &larr;
        </Button>
        <strong>{conversation.title ?? t('page.newConversationFallback')}</strong>
      </div>

      <p className="asa-assistant__disclaimer">{t('page.disclaimer')}</p>

      <div className="asa-assistant__messages">
        {conversation.messages.map((message) => (
          <div key={message.id} className={`asa-assistant-message asa-assistant-message--${message.role}`}>
            <div className="asa-assistant-message__bubble">
              {message.role === 'assistant' ? <AssistantBubble content={message.content} /> : message.content}
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
                  {t('conversation.tryAgain')}
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
          placeholder={t('conversation.askPlaceholder')}
          aria-label={t('conversation.askAriaLabel')}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
        />
        {sending ? (
          <Button type="button" variant="outline" onClick={() => cancelAIStream()}>
            {t('conversation.cancel')}
          </Button>
        ) : (
          <Button type="submit" loading={sending} disabled={!draft.trim()}>
            {t('conversation.ask')}
          </Button>
        )}
      </form>
    </div>
  )
}

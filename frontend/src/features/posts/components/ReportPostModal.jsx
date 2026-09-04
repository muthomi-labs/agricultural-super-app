import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Modal, Textarea } from '@/components/ui'
import { errorMessage } from '@/features/auth/AuthContext'
import { postsService } from '@/services'

const REASON_VALUES = ['spam', 'harassment', 'scam', 'misleading', 'inappropriate', 'other']

export function ReportPostModal({ postId, open, onClose }) {
  const { t } = useTranslation('posts')
  const [reason, setReason] = useState('spam')
  const [details, setDetails] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  function handleClose() {
    setReason('spam')
    setDetails('')
    setError(null)
    setDone(false)
    onClose()
  }

  async function handleSubmit() {
    setSubmitting(true)
    setError(null)
    try {
      await postsService.reportPost(postId, reason, details.trim())
      setDone(true)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} title={t('report.title')} onClose={handleClose}>
      {done ? (
        <>
          <p>{t('report.thanks')}</p>
          <div className="asa-post-menu__actions">
            <Button variant="primary" onClick={handleClose}>
              {t('report.close')}
            </Button>
          </div>
        </>
      ) : (
        <>
          <p>{t('report.reasonPrompt')}</p>
          <div className="asa-report-modal__reasons" role="radiogroup" aria-label={t('report.reasonPrompt')}>
            {REASON_VALUES.map((value) => (
              <label key={value} className="asa-report-modal__reason">
                <input
                  type="radio"
                  name="report-reason"
                  value={value}
                  checked={reason === value}
                  onChange={() => setReason(value)}
                />
                <span>{t(`report.reasons.${value}`)}</span>
              </label>
            ))}
          </div>
          <Textarea
            label={t('report.detailsLabel')}
            name="report-details"
            rows={3}
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            placeholder={t('report.detailsPlaceholder')}
          />
          {error && <p className="asa-post-menu__error">{error}</p>}
          <div className="asa-post-menu__actions">
            <Button variant="secondary" onClick={handleClose} disabled={submitting}>
              {t('report.cancel')}
            </Button>
            <Button variant="danger" onClick={handleSubmit} loading={submitting}>
              {t('report.submit')}
            </Button>
          </div>
        </>
      )}
    </Modal>
  )
}

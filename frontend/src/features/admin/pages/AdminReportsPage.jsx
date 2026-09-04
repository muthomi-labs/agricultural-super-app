import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Badge, Button, EmptyState, ErrorState, LoadingState, PageHeader, Tabs } from '@/components/ui'
import { formatRelativeTime } from '@/lib/format'
import { errorMessage } from '@/features/auth/AuthContext'
import { adminService } from '@/services'
import '../admin.css'

export function AdminReportsPage() {
  const { t } = useTranslation('admin')
  const STATUS_TABS = [
    { value: 'pending', label: t('reports.tabs.pending') },
    { value: 'reviewed', label: t('reports.tabs.reviewed') },
    { value: 'dismissed', label: t('reports.tabs.dismissed') },
    { value: '', label: t('reports.tabs.all') },
  ]
  const [status, setStatus] = useState('pending')
  const [reports, setReports] = useState([])
  const [loadStatus, setLoadStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [reviewingId, setReviewingId] = useState(null)

  function load() {
    setLoadStatus('loading')
    adminService
      .listReports({ status: status || undefined, perPage: 50 })
      .then((result) => {
        setReports(result.items)
        setLoadStatus('ready')
      })
      .catch((err) => {
        setError(errorMessage(err))
        setLoadStatus('error')
      })
  }

  useEffect(load, [status])

  async function handleReview(reportId, nextStatus) {
    setReviewingId(reportId)
    try {
      await adminService.reviewReport(reportId, nextStatus)
      setReports((prev) =>
        status
          ? prev.filter((r) => r.id !== reportId)
          : prev.map((r) => (r.id === reportId ? { ...r, status: nextStatus } : r)),
      )
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setReviewingId(null)
    }
  }

  return (
    <>
      <PageHeader title={t('reports.title')} subtitle={t('reports.subtitle')} />

      <Tabs items={STATUS_TABS} value={status} onChange={setStatus} className="asa-profile-tabs" />

      {loadStatus === 'loading' && <LoadingState label={t('reports.loading')} />}
      {loadStatus === 'error' && <ErrorState message={error ?? undefined} onRetry={load} />}
      {loadStatus === 'ready' && reports.length === 0 && (
        <EmptyState title={t('reports.emptyTitle')} description={t('reports.emptyDescription')} icon="🚩" />
      )}

      {loadStatus === 'ready' && reports.length > 0 && (
        <div className="asa-admin-list">
          {reports.map((report) => (
            <div key={report.id} className="asa-admin-list-row">
              <div className="asa-admin-list-row__body">
                {report.post ? (
                  <Link to={`/posts/${report.post.id}`} className="asa-admin-list-row__title">
                    {report.post.title}
                  </Link>
                ) : (
                  <span className="asa-admin-list-row__title">{t('reports.postUnavailable')}</span>
                )}
                <span className="asa-admin-list-row__meta">
                  {t('reports.reportedByMeta', {
                    name: report.reporter.user.username,
                    reason: t(`reports.reasons.${report.reason}`, { defaultValue: report.reason }),
                    time: formatRelativeTime(report.createdAt),
                  })}
                </span>
                {report.details && <span className="asa-admin-list-row__quote">"{report.details}"</span>}
              </div>
              <div className="asa-admin-list-row__actions">
                <Badge variant={report.status === 'pending' ? 'warning' : 'default'}>
                  {t(`reports.status.${report.status}`, { defaultValue: report.status })}
                </Badge>
                {report.status === 'pending' && (
                  <>
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={reviewingId === report.id}
                      onClick={() => handleReview(report.id, 'dismissed')}
                    >
                      {t('reports.dismiss')}
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      loading={reviewingId === report.id}
                      onClick={() => handleReview(report.id, 'reviewed')}
                    >
                      {t('reports.markReviewed')}
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

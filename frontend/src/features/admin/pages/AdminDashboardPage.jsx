import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Badge, Card, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { formatRelativeTime } from '@/lib/format'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { fetchAdminStats } from '@/store/slices/adminSlice'
import '../admin.css'

function StatCard({ label, value, meta }) {
  return (
    <Card className="asa-admin-stat-card" padded>
      <p className="asa-admin-stat-card__label">{label}</p>
      <p className="asa-admin-stat-card__value">{value}</p>
      {meta && <p className="asa-admin-stat-card__meta">{meta}</p>}
    </Card>
  )
}

export function AdminDashboardPage() {
  const { t } = useTranslation('admin')
  const dispatch = useAppDispatch()
  const stats = useAppSelector((state) => state.admin.stats)
  const status = useAppSelector((state) => state.admin.statsStatus)
  const error = useAppSelector((state) => state.admin.statsError)

  useEffect(() => {
    dispatch(fetchAdminStats())
  }, [dispatch])

  if (status === 'loading' || status === 'idle') return <LoadingState label={t('dashboard.loading')} />
  if (status === 'error' || !stats) {
    return <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchAdminStats())} />
  }

  return (
    <>
      <PageHeader title={t('dashboard.title')} subtitle={t('dashboard.subtitle')} />

      <div className="asa-admin-stats">
        <StatCard
          label={t('dashboard.totalUsers')}
          value={stats.users.total}
          meta={t('dashboard.activeInactive', { active: stats.users.active, inactive: stats.users.inactive })}
        />
        <StatCard
          label={t('dashboard.byRole')}
          value={stats.users.by_role.farmer}
          meta={t('dashboard.roleBreakdown', { expert: stats.users.by_role.expert, admin: stats.users.by_role.admin })}
        />
        <StatCard
          label={t('dashboard.posts')}
          value={stats.posts.total}
          meta={t('dashboard.commentsCount', { count: stats.comments.total })}
        />
        <StatCard label={t('dashboard.communities')} value={stats.communities.total} />
        <Link to="/admin/reports" className="asa-admin-stat-card-link">
          <StatCard
            label={t('dashboard.reports')}
            value={stats.reports.pending}
            meta={t('dashboard.reportsMeta', { total: stats.reports.total })}
          />
        </Link>
        <StatCard
          label={t('dashboard.conversations')}
          value={stats.conversations.total}
          meta={t('dashboard.messagesSent', { count: stats.messages.total })}
        />
        <StatCard
          label={t('dashboard.aiAssistant')}
          value={stats.ai.configured ? t('dashboard.aiConfigured') : t('dashboard.aiNotConfigured')}
          meta={t('dashboard.aiProviderMeta', { provider: stats.ai.provider }) + (stats.ai.model ? ` · ${stats.ai.model}` : '')}
        />
      </div>

      <section className="asa-admin-section">
        <h2 className="asa-admin-section__title">{t('dashboard.recentRegistrations')}</h2>
        <Card padded>
          {stats.recentUsers.length === 0 ? (
            <p className="asa-admin-list-row__meta">{t('dashboard.noUsersYet')}</p>
          ) : (
            <div className="asa-admin-list">
              {stats.recentUsers.map((u) => (
                <div key={u.user.id} className="asa-admin-list-row">
                  <div className="asa-admin-list-row__body">
                    <Link to="/admin/users" className="asa-admin-list-row__title">
                      {u.user.username}
                    </Link>
                    <span className="asa-admin-list-row__meta">
                      {u.user.email} · {t('dashboard.joined', { time: formatRelativeTime(u.user.createdAt) })}
                    </span>
                  </div>
                  <Badge>{t(`common:roles.${u.user.role}`)}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>

      <section className="asa-admin-section">
        <h2 className="asa-admin-section__title">{t('dashboard.recentPosts')}</h2>
        <Card padded>
          {stats.recentPosts.length === 0 ? (
            <p className="asa-admin-list-row__meta">{t('dashboard.noPostsYet')}</p>
          ) : (
            <div className="asa-admin-list">
              {stats.recentPosts.map((post) => (
                <div key={post.id} className="asa-admin-list-row">
                  <div className="asa-admin-list-row__body">
                    <Link to={`/posts/${post.id}`} className="asa-admin-list-row__title">
                      {post.title}
                    </Link>
                    <span className="asa-admin-list-row__meta">
                      {t('dashboard.by', { name: post.author.user.username })} · {formatRelativeTime(post.createdAt)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>
    </>
  )
}

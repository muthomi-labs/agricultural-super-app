import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Button, EmptyState, ErrorState, LoadingState, PageHeader } from '@/components/ui'
import { formatRelativeTime, groupByDay } from '@/lib/format'
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/store/slices/notificationsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import '../notifications.css'

function actorName(actor) {
  return actor.profile.firstName && actor.profile.lastName
    ? `${actor.profile.firstName} ${actor.profile.lastName}`
    : actor.user.username
}

function notificationText(t, notification) {
  const name = actorName(notification.actor)
  const target = notification.isReel ? 'reel' : 'post'
  if (notification.type === 'post_like') return t(`text.post_like.${target}`, { name })
  if (notification.type === 'post_comment') return t(`text.post_comment.${target}`, { name })
  if (notification.type === 'comment_reply') return t('text.comment_reply', { name })
  if (notification.type === 'follow') return t('text.follow', { name })
  return t('text.default', { name })
}

function notificationLink(notification) {
  if (notification.postId) return `/posts/${notification.postId}`
  return `/experts/${notification.actor.user.id}`
}

export function NotificationsPage() {
  const { t } = useTranslation('notifications')
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const notifications = useAppSelector((state) => state.notifications.items)
  const status = useAppSelector((state) => state.notifications.status)
  const error = useAppSelector((state) => state.notifications.error)
  const hasUnread = notifications.some((n) => !n.isRead)

  useEffect(() => {
    dispatch(fetchNotifications())
  }, [dispatch])

  function handleOpen(notification) {
    if (!notification.isRead) dispatch(markNotificationRead(notification.id))
    navigate(notificationLink(notification))
  }

  return (
    <>
      <PageHeader
        title={t('title')}
        subtitle={t('subtitle')}
        actions={
          hasUnread ? (
            <Button variant="secondary" size="sm" onClick={() => dispatch(markAllNotificationsRead())}>
              {t('markAllRead')}
            </Button>
          ) : undefined
        }
      />

      {status === 'loading' && <LoadingState label={t('loading')} />}
      {status === 'error' && (
        <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchNotifications())} />
      )}
      {status === 'ready' && notifications.length === 0 && (
        <EmptyState
          title={t('emptyTitle')}
          description={t('emptyDescription')}
          icon="🔔"
        />
      )}

      {status === 'ready' &&
        groupByDay(notifications, 'createdAt').map(([label, items]) => (
          <section key={label} className="asa-notifications__group">
            <h2 className="asa-notifications__group-title">{t(`groups.${label}`)}</h2>
            <ul className="asa-notifications__list">
              {items.map((notification) => (
                <li key={notification.id}>
                  <button
                    type="button"
                    className={`asa-notifications__item ${notification.isRead ? '' : 'asa-notifications__item--unread'}`}
                    onClick={() => handleOpen(notification)}
                  >
                    <Avatar
                      imageUrl={notification.actor.profile.profileImageUrl}
                      name={actorName(notification.actor)}
                      username={notification.actor.user.username}
                      size="md"
                    />
                    <span className="asa-notifications__body">
                      <span className="asa-notifications__text">
                        {notificationText(t, notification)}
                        {notification.postTitle && <> — <em>{notification.postTitle}</em></>}
                      </span>
                      <span className="asa-notifications__time">{formatRelativeTime(notification.createdAt)}</span>
                    </span>
                    {!notification.isRead && <span className="asa-notifications__dot" aria-hidden="true" />}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
    </>
  )
}

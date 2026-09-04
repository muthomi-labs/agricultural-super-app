import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Badge, Button, EmptyState, ErrorState, LoadingState, Tabs, VerifiedBadge } from '@/components/ui'
import { useAuth } from '@/features/auth/AuthContext'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import {
  fetchCommunity,
  removeCommunityMember,
  setMemberRole,
  toggleMembership,
} from '@/store/slices/communitiesSlice'
import { fetchCommunityPosts } from '@/store/slices/postsSlice'
import { PostCard } from '@/features/posts/components/PostCard'
import { QuickComposer } from '@/features/posts/components/QuickComposer'
import { UsersIcon } from '@/components/icons'
import { formatCount, formatDate } from '@/lib/format'
import { canPostInCommunity } from '../permissions'
import { CommunitySettingsModal } from '../components/CommunitySettingsModal'
import '../communities.css'

export function CommunityDetailPage() {
  const { t } = useTranslation('communities')
  const TABS = [
    { value: 'announcements', label: t('detail.tabs.announcements') },
    { value: 'feed', label: t('detail.tabs.feed') },
    { value: 'members', label: t('detail.tabs.members') },
    { value: 'about', label: t('detail.tabs.about') },
  ]
  const { communityId } = useParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { user } = useAuth()
  const [tab, setTab] = useState('feed')
  const [settingsOpen, setSettingsOpen] = useState(false)

  const community = useAppSelector((state) => state.communities.current)
  const status = useAppSelector((state) => state.communities.currentStatus)
  const error = useAppSelector((state) => state.communities.currentError)
  const loading = useAppSelector((state) => state.communities.membershipLoadingId === Number(communityId))
  const memberActionLoadingUserId = useAppSelector((state) => state.communities.memberActionLoadingUserId)

  const posts = useAppSelector((state) => state.posts.communityPosts)
  const postsStatus = useAppSelector((state) => state.posts.communityPostsStatus)
  const postsError = useAppSelector((state) => state.posts.communityPostsError)

  useEffect(() => {
    if (communityId) dispatch(fetchCommunity(Number(communityId)))
  }, [dispatch, communityId])

  useEffect(() => {
    if (communityId) dispatch(fetchCommunityPosts(Number(communityId)))
  }, [dispatch, communityId])

  if (status === 'loading') return <LoadingState label={t('detail.loading')} />
  if (status === 'error' || !community) {
    return <ErrorState message={error ?? undefined} onRetry={() => dispatch(fetchCommunity(Number(communityId)))} />
  }

  const isMember = community.members.some((m) => m.userId === user?.user.id)
  const isCreator = community.createdBy === user?.user.id
  const isAdmin = community.myRole === 'admin'
  const userRole = user?.user.role
  const allowedToPost = isMember && canPostInCommunity(community, userRole)
  const announcements = posts.filter((post) => post.isAnnouncement)

  function handleToggleMembership() {
    if (loading) return
    dispatch(toggleMembership({ communityId: community.id, userId: user.user.id }))
  }

  function handleSetRole(targetUserId, role) {
    dispatch(setMemberRole({ communityId: community.id, userId: targetUserId, role }))
  }

  function handleRemoveMember(targetUserId) {
    dispatch(removeCommunityMember({ communityId: community.id, userId: targetUserId }))
  }

  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => navigate('/communities')}>
        &larr; {t('detail.backToCommunities')}
      </Button>

      <section className="asa-community-hero">
        {community.imageUrl && <img className="asa-community-hero__image" src={community.imageUrl} alt="" />}
        <div className="asa-community-hero__header">
          <div className="asa-community-hero__identity">
            {!community.imageUrl && (
              <span className="asa-community-hero__avatar asa-community-hero__avatar--placeholder" aria-hidden="true">
                <UsersIcon width={28} height={28} />
              </span>
            )}
            <div>
              <h1 className="asa-community-hero__name">
                <span>{community.name}</span>
                {isAdmin && <Badge variant="default">{t('detail.admin')}</Badge>}
              </h1>
              <p className="asa-community-hero__meta">
                {t('card.members', {
                  count: community.members.length,
                  formatted: formatCount(community.members.length),
                })}{' '}
                · {t('detail.createdBy')}{' '}
                {community.creator?.profile.firstName || community.creator?.user.username}
              </p>
            </div>
          </div>
          <div className="asa-community-hero__actions">
            {isAdmin && (
              <Button variant="secondary" onClick={() => setSettingsOpen(true)}>
                {t('detail.communitySettings')}
              </Button>
            )}
            {!isCreator && (
              <Button
                variant={isMember ? 'secondary' : 'primary'}
                onClick={handleToggleMembership}
                loading={loading}
                aria-pressed={isMember}
              >
                {isMember ? t('detail.leaveCommunity') : t('detail.joinCommunity')}
              </Button>
            )}
          </div>
        </div>
        {community.description && <p>{community.description}</p>}
      </section>

      <Tabs items={TABS} value={tab} onChange={setTab} className="asa-community-tabs" />

      {tab === 'announcements' && (
        <>
          {announcements.length === 0 ? (
            <EmptyState
              title={t('detail.noAnnouncementsTitle')}
              description={t('detail.noAnnouncementsDescription')}
              icon="📢"
            />
          ) : (
            announcements.map((post) => <PostCard key={post.id} post={post} />)
          )}
        </>
      )}

      {tab === 'feed' && (
        <>
          {allowedToPost && (
            <QuickComposer
              communityId={community.id}
              placeholder={t('detail.composerPlaceholder', { name: community.name })}
              allowAnnouncement={isAdmin}
              onPosted={() => dispatch(fetchCommunityPosts(community.id))}
            />
          )}
          {!allowedToPost && isMember && (
            <p className="asa-community-join-hint">
              {community.postingPermission === 'experts_only'
                ? t('detail.onlyExpertsCanPost')
                : t('detail.onlyAdminsCanPost')}
            </p>
          )}
          {!isMember && <p className="asa-community-join-hint">{t('detail.joinToPost')}</p>}

          {postsStatus === 'loading' && <LoadingState label={t('detail.loadingPosts')} />}
          {postsStatus === 'error' && (
            <ErrorState message={postsError ?? undefined} onRetry={() => dispatch(fetchCommunityPosts(community.id))} />
          )}
          {postsStatus === 'ready' && posts.length === 0 && (
            <EmptyState
              title={t('detail.noPostsTitle')}
              description={t('detail.noPostsDescription')}
              icon="🌾"
            />
          )}
          {postsStatus === 'ready' && posts.map((post) => <PostCard key={post.id} post={post} />)}
        </>
      )}

      {tab === 'members' && (
        <>
          {community.members.length === 0 ? (
            <EmptyState title={t('detail.noMembers')} icon="👥" />
          ) : (
            <ul className="asa-community-members">
              {community.members.map((membership) => {
                const member = membership.member
                const name =
                  member?.profile.firstName && member?.profile.lastName
                    ? `${member.profile.firstName} ${member.profile.lastName}`
                    : member?.user.username
                const isRowCreator = community.createdBy === member?.user.id
                const rowLoading = memberActionLoadingUserId === member?.user.id
                return (
                  <li key={membership.id} className="asa-community-member">
                    <div className="asa-community-member-row">
                      <Avatar imageUrl={member?.profile.profileImageUrl} name={name} username={member?.user.username} size="sm" />
                      <div className="asa-community-member-row__identity">
                        <span className="asa-community-member__name">{name}</span>
                        <VerifiedBadge profile={member?.profile ?? { isVerified: false }} />
                      </div>
                      <div className="asa-community-member-row__badges">
                        {member?.user.role === 'expert' && <Badge variant="default">{t('detail.expertBadge')}</Badge>}
                        {isRowCreator ? (
                          <span className="asa-community-member__badge">{t('detail.creatorBadge')}</span>
                        ) : membership.role === 'admin' ? (
                          <span className="asa-community-member__badge">{t('detail.adminBadge')}</span>
                        ) : null}
                      </div>
                      {isAdmin && !isRowCreator && (
                        <div className="asa-community-member-row__actions">
                          <Button
                            variant="ghost"
                            size="sm"
                            loading={rowLoading}
                            onClick={() => handleSetRole(member.user.id, membership.role === 'admin' ? 'member' : 'admin')}
                          >
                            {membership.role === 'admin' ? t('detail.demote') : t('detail.promote')}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            loading={rowLoading}
                            onClick={() => handleRemoveMember(member.user.id)}
                          >
                            {t('detail.remove')}
                          </Button>
                        </div>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </>
      )}

      {tab === 'about' && (
        <div className="asa-community-about">
          <p>{community.description || t('detail.noDescription')}</p>
          <dl>
            <dt>{t('detail.aboutCreatedBy')}</dt>
            <dd>{community.creator?.profile.firstName || community.creator?.user.username}</dd>
            <dt>{t('detail.aboutCreatedOn')}</dt>
            <dd>{formatDate(community.createdAt)}</dd>
            <dt>{t('detail.aboutMembers')}</dt>
            <dd>{community.members.length}</dd>
            <dt>{t('detail.aboutWhoCanPost')}</dt>
            <dd>{t(`detail.permissions.${community.postingPermission}`)}</dd>
            <dt>{t('detail.aboutWhoCanComment')}</dt>
            <dd>
              {community.commentsEnabled
                ? t(`detail.permissions.${community.messagingPermission}`)
                : t('detail.commentsClosed')}
            </dd>
          </dl>
        </div>
      )}

      {settingsOpen && (
        <CommunitySettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} community={community} />
      )}
    </>
  )
}

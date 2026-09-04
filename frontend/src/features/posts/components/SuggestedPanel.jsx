import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Avatar, Button } from '@/components/ui'
import { fetchExperts, fetchMyFollowing } from '@/store/slices/expertsSlice'
import { fetchCommunities, toggleMembership } from '@/store/slices/communitiesSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { useAuth } from '@/features/auth/AuthContext'
import { formatCount } from '@/lib/format'
import { FollowButton } from '@/features/experts/components/FollowButton'

function displayName(profile) {
  return profile.firstName && profile.lastName ? `${profile.firstName} ${profile.lastName}` : null
}

export function SuggestedPanel() {
  const { t } = useTranslation('posts')
  const dispatch = useAppDispatch()
  const { user } = useAuth()
  const experts = useAppSelector((state) => state.experts.experts)
  const followingIds = useAppSelector((state) => state.experts.followingIds)
  const communities = useAppSelector((state) => state.communities.list)
  const membershipLoadingId = useAppSelector((state) => state.communities.membershipLoadingId)

  useEffect(() => {
    dispatch(fetchExperts({ page: 1, pageSize: 5 }))
    dispatch(fetchMyFollowing())
    dispatch(fetchCommunities({ page: 1, pageSize: 4 }))
  }, [dispatch])

  const suggestedFarmers = experts.filter((e) => e.user.id !== user?.user.id && !followingIds.includes(e.user.id)).slice(0, 4)
  const suggestedCommunities = communities.filter((c) => !c.members.some((m) => m.userId === user?.user.id)).slice(0, 3)

  if (suggestedFarmers.length === 0 && suggestedCommunities.length === 0) return null

  return (
    <aside className="asa-suggested-panel">
      {suggestedFarmers.length > 0 && (
        <section className="asa-suggested-panel__section">
          <h2 className="asa-suggested-panel__title">{t('suggested.farmersToFollow')}</h2>
          <ul className="asa-suggested-panel__list">
            {suggestedFarmers.map((expert) => {
              const name = displayName(expert.profile) ?? expert.user.username
              return (
                <li key={expert.user.id} className="asa-suggested-panel__row">
                  <Link to={`/experts/${expert.user.id}`}>
                    <Avatar imageUrl={expert.profile.profileImageUrl} name={name} username={expert.user.username} size="sm" />
                  </Link>
                  <Link to={`/experts/${expert.user.id}`} className="asa-suggested-panel__name">
                    {name}
                  </Link>
                  <FollowButton userId={expert.user.id} isFollowing={false} name={name} />
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {suggestedCommunities.length > 0 && (
        <section className="asa-suggested-panel__section">
          <h2 className="asa-suggested-panel__title">{t('suggested.communitiesToJoin')}</h2>
          <ul className="asa-suggested-panel__list">
            {suggestedCommunities.map((community) => (
              <li key={community.id} className="asa-suggested-panel__row">
                <Link to={`/communities/${community.id}`} className="asa-suggested-panel__name">
                  🌾 {community.name}
                  <small>
                    {formatCount(community.members.length)} {t('suggested.members')}
                  </small>
                </Link>
                <Button
                  size="sm"
                  loading={membershipLoadingId === community.id}
                  onClick={() => dispatch(toggleMembership({ communityId: community.id, userId: user.user.id }))}
                >
                  {t('suggested.join')}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  )
}

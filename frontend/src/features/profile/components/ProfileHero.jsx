import { useTranslation } from 'react-i18next'
import { Avatar } from '@/components/ui'
import { VerifiedBadge } from '@/components/ui'
import '@/features/experts/experts.css'

export function ProfileHero({ profile, followersCount, followingCount, postsCount, onFollowingClick, actions }) {
  const { t } = useTranslation(['profile', 'common'])
  const name =
    profile.profile.firstName && profile.profile.lastName
      ? `${profile.profile.firstName} ${profile.profile.lastName}`
      : profile.user.username

  return (
    <section className="asa-profile-hero">
      <div className="asa-profile-hero__row">
        <Avatar
          imageUrl={profile.profile.profileImageUrl}
          name={name}
          username={profile.user.username}
          size="xl"
        />
        <div>
          <div className="asa-profile-hero__name-row">
            <h1 className="asa-profile-hero__name">{name}</h1>
            <VerifiedBadge profile={profile.profile} />
          </div>
          <span className="asa-profile-hero__username">@{profile.user.username}</span>
          {profile.profile.location && (
            <span className="asa-profile-hero__location">{profile.profile.location}</span>
          )}
          {profile.profile.bio && <p className="asa-profile-hero__bio">{profile.profile.bio}</p>}
          <div className="asa-profile-hero__stats">
            {typeof postsCount === 'number' && (
              <span>
                <span className="asa-profile-hero__stat">{postsCount}</span> {t('profile:hero.posts')}
              </span>
            )}
            {typeof followersCount === 'number' && (
              <span>
                <span className="asa-profile-hero__stat">{followersCount}</span> {t('profile:hero.followers')}
              </span>
            )}
            {typeof followingCount === 'number' &&
              (onFollowingClick ? (
                <button type="button" className="asa-profile-hero__stat-btn" onClick={onFollowingClick}>
                  <span className="asa-profile-hero__stat">{followingCount}</span> {t('profile:hero.following')}
                </button>
              ) : (
                <span>
                  <span className="asa-profile-hero__stat">{followingCount}</span> {t('profile:hero.following')}
                </span>
              ))}
            <span>
              <span className="asa-profile-hero__stat">{t(`common:roles.${profile.user.role}`)}</span>
            </span>
          </div>
        </div>
      </div>
      {actions && <div className="asa-profile-hero__actions">{actions}</div>}
    </section>
  )
}
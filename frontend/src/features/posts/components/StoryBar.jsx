import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/features/auth/AuthContext'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import { fetchActiveStories } from '@/store/slices/storiesSlice'
import { StoryViewer } from '@/features/stories/components/StoryViewer'
import { StoryItem } from './StoryItem'

function displayName(actor) {
  return actor.profile.firstName && actor.profile.lastName
    ? `${actor.profile.firstName} ${actor.profile.lastName}`
    : actor.user.username
}

/** Horizontal "Stories" bar at the top of the feed. Backed by real Story
 * records from the API (see storiesSlice/fetchActiveStories) -- each of
 * which the backend already guarantees is currently active (expires_at
 * > now); this component never re-derives expiration itself. */
export function StoryBar() {
  const { t } = useTranslation('stories')
  const { user } = useAuth()
  const dispatch = useAppDispatch()
  const stories = useAppSelector((state) => state.stories.active)
  const [openIndex, setOpenIndex] = useState(null)

  useEffect(() => {
    dispatch(fetchActiveStories())
  }, [dispatch])

  const groups = useMemo(() => {
    const order = []
    const byAuthor = new Map()
    for (const story of stories) {
      if (!byAuthor.has(story.userId)) {
        byAuthor.set(story.userId, { author: story.author, slides: [] })
        order.push(story.userId)
      }
      byAuthor.get(story.userId).slides.push(story)
    }
    return order.map((userId) => {
      const { author, slides } = byAuthor.get(userId)
      return {
        authorId: userId,
        authorName: displayName(author),
        authorUsername: author.user.username,
        authorImageUrl: author.profile.profileImageUrl,
        slides,
      }
    })
  }, [stories])

  const ownGroupIndex = user ? groups.findIndex((group) => group.authorId === user.user.id) : -1
  const hasOwnStory = ownGroupIndex !== -1
  const otherGroups = groups.filter((_, index) => index !== ownGroupIndex)

  return (
    <div className="asa-story-bar">
      {user && !hasOwnStory && (
        <StoryItem
          to="/create/story"
          isAdd
          imageUrl={user.profile.profileImageUrl}
          name={displayName(user)}
          username={user.user.username}
          label={t('bar.yourStory')}
        />
      )}
      {user && hasOwnStory && (
        <StoryItem
          onClick={() => setOpenIndex(ownGroupIndex)}
          imageUrl={user.profile.profileImageUrl}
          name={displayName(user)}
          username={user.user.username}
          label={t('bar.yourStory')}
        />
      )}

      {otherGroups.map((group) => (
        <StoryItem
          key={group.authorId}
          onClick={() => setOpenIndex(groups.indexOf(group))}
          imageUrl={group.authorImageUrl}
          name={group.authorName}
          username={group.authorUsername}
          label={group.authorName.split(' ')[0]}
        />
      ))}

      {openIndex !== null && (
        <StoryViewer stories={groups} startIndex={openIndex} onClose={() => setOpenIndex(null)} />
      )}
    </div>
  )
}

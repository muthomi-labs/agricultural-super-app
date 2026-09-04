import { useTranslation } from 'react-i18next'
import { Button, Toast, useToast } from '@/components/ui'
import { toggleFollow } from '@/store/slices/expertsSlice'
import { useAppDispatch, useAppSelector } from '@/store/hooks'

export function FollowButton({ userId, isFollowing, name }) {
  const { t } = useTranslation('experts')
  const dispatch = useAppDispatch()
  const loading = useAppSelector((state) => state.experts.followLoadingUserId === userId)
  const { message, showToast } = useToast()

  async function handleToggle() {
    if (loading) return
    const result = await dispatch(toggleFollow(userId))
    if (toggleFollow.fulfilled.match(result) && name) {
      const nowFollowing = result.payload.summary.followingIds.includes(userId)
      showToast(nowFollowing ? t('follow.nowFollowing', { name }) : t('follow.unfollowed', { name }))
    }
  }

  return (
    <>
      <Button
        variant={isFollowing ? 'secondary' : 'primary'}
        size="sm"
        onClick={handleToggle}
        loading={loading}
        aria-pressed={isFollowing}
      >
        {isFollowing ? t('follow.following') : t('follow.follow')}
      </Button>
      <Toast message={message} />
    </>
  )
}
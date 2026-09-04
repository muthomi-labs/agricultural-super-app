function emptyProfile() {
  return {
    id: null,
    userId: null,
    firstName: null,
    lastName: null,
    bio: null,
    location: null,
    profileImageUrl: null,
    phoneNumber: null,
    isVerified: false,
    createdAt: null,
    updatedAt: null,
  }
}

export function normalizeProfile(p) {
  if (!p) return emptyProfile()
  return {
    id: p.id,
    userId: p.user_id,
    firstName: p.first_name ?? null,
    lastName: p.last_name ?? null,
    bio: p.bio ?? null,
    location: p.location ?? null,
    profileImageUrl: p.profile_image_url ?? null,
    phoneNumber: p.phone_number ?? null,
    isVerified: p.is_verified ?? false,
    createdAt: p.created_at,
    updatedAt: p.updated_at,
  }
}

export function toUserProfile(u) {
  if (!u) return null
  return {
    user: {
      id: u.id,
      username: u.username,
      email: u.email ?? null,
      role: u.role,
      language: u.language ?? 'en',
      isActive: u.is_active ?? true,
      createdAt: u.created_at,
      updatedAt: u.updated_at,
    },
    profile: normalizeProfile(u.profile),
  }
}

export function normalizeImage(img) {
  return {
    id: img.id,
    postId: img.post_id,
    imageUrl: img.image_url,
    createdAt: img.created_at,
  }
}

export function normalizeComment(c) {
  return {
    id: c.id,
    postId: c.post_id,
    parentCommentId: c.parent_comment_id ?? null,
    content: c.content,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    author: toUserProfile(c.author),
  }
}

export function normalizePost(p) {
  return {
    id: p.id,
    title: p.title,
    content: p.content,
    videoUrl: p.video_url ?? null,
    viewCount: p.view_count ?? 0,
    createdAt: p.created_at,
    updatedAt: p.updated_at,
    author: toUserProfile(p.author),
    images: (p.images ?? []).map(normalizeImage),
    comments: (p.comments ?? []).map(normalizeComment),
    likeCount: p.like_count ?? 0,
    likedByMe: p.liked_by_me ?? false,
    communityId: p.community_id ?? null,
    originalPostId: p.original_post_id ?? null,
    originalPost: p.original_post ? normalizePost(p.original_post) : null,
    reactionCounts: p.reaction_counts ?? {},
    myReaction: p.my_reaction ?? null,
    saveCount: p.save_count ?? 0,
    savedByMe: p.saved_by_me ?? false,
    repostCount: p.repost_count ?? 0,
    repostedByMe: p.reposted_by_me ?? false,
    isAnnouncement: p.is_announcement ?? false,
    commentsOpen: p.comments_open ?? true,
  }
}

export function normalizeStory(s) {
  return {
    id: s.id,
    userId: s.user_id,
    imageUrl: s.image_url,
    caption: s.caption ?? null,
    createdAt: s.created_at,
    expiresAt: s.expires_at,
    author: toUserProfile(s.author),
  }
}

export function normalizeMembership(m) {
  return {
    id: m.id,
    userId: m.user_id,
    communityId: m.community_id,
    role: m.role ?? 'member',
    joinedAt: m.joined_at,
    member: toUserProfile(m.member),
  }
}

export function normalizeCommunity(c) {
  return {
    id: c.id,
    name: c.name,
    description: c.description ?? null,
    imageUrl: c.image_url ?? null,
    createdBy: c.created_by,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    creator: toUserProfile(c.creator),
    members: (c.members ?? []).map(normalizeMembership),
    postingPermission: c.posting_permission ?? 'everyone',
    messagingPermission: c.messaging_permission ?? 'everyone',
    commentsEnabled: c.comments_enabled ?? true,
    myRole: c.my_role ?? null,
  }
}

export function normalizeParticipant(p) {
  return {
    id: p.id,
    conversationId: p.conversation_id,
    userId: p.user_id,
    joinedAt: p.joined_at,
    participant: toUserProfile(p.participant),
  }
}

export function normalizeMessage(m) {
  return {
    id: m.id,
    conversationId: m.conversation_id,
    senderId: m.sender_id,
    content: m.content,
    isRead: m.is_read ?? false,
    createdAt: m.created_at,
    sender: toUserProfile(m.sender),
  }
}

export function normalizeConversation(c) {
  return {
    id: c.id,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    participants: (c.participants ?? []).map(normalizeParticipant),
    messages: (c.messages ?? []).map(normalizeMessage),
  }
}

export function normalizeAIMessage(m) {
  return {
    id: m.id,
    conversationId: m.conversation_id,
    role: m.role,
    content: m.content,
    createdAt: m.created_at,
  }
}

export function normalizeAIConversation(c) {
  return {
    id: c.id,
    title: c.title ?? null,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    messages: (c.messages ?? []).map(normalizeAIMessage),
  }
}

export function normalizeNotification(n) {
  return {
    id: n.id,
    type: n.type,
    isRead: n.is_read,
    createdAt: n.created_at,
    postId: n.post_id ?? null,
    commentId: n.comment_id ?? null,
    postTitle: n.post_title ?? null,
    isReel: n.is_reel ?? false,
    actor: toUserProfile(n.actor),
  }
}

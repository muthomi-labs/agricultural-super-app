/** Small formatting helpers shared across the UI. */

import i18n from '@/i18n'

const DATE_FORMAT_OPTS = {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
}

// The backend serializes timestamps as naive UTC (e.g. "2026-08-26T06:16:57.274690"),
// with no "Z" or offset. `new Date(...)` treats a designator-less string as local
// time per the ECMA-262 spec, so without this, every timestamp is shifted by the
// browser's UTC offset. Append "Z" only when no timezone designator is already present.
export function asUtcDate(value) {
  if (typeof value === 'string' && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(value)) {
    return new Date(`${value}Z`)
  }
  return new Date(value)
}

export function formatDate(value) {
  // i18n.language drives this (rather than the browser's own locale) so
  // a date renders with Kiswahili month names whenever that's the
  // selected app language, regardless of the device's own locale.
  return asUtcDate(value).toLocaleDateString(i18n.language, DATE_FORMAT_OPTS)
}

export function formatRelativeTime(value) {
  const then = asUtcDate(value).getTime()
  const now = Date.now()
  const diffMs = Math.max(0, now - then)
  const minutes = Math.floor(diffMs / 60_000)

  if (minutes < 1) return i18n.t('common:time.justNow')
  if (minutes < 60) return i18n.t('common:time.minutesAgo', { count: minutes })

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return i18n.t('common:time.hoursAgo', { count: hours })

  const days = Math.floor(hours / 24)
  if (days < 7) return i18n.t('common:time.daysAgo', { count: days })

  return formatDate(value)
}

/** Posts still need a `title` at the API layer (required, non-null column),
 * but the composer UI is caption-only now -- this derives a short title
 * from the caption so the requirement never surfaces to the user. */
export function deriveTitle(content) {
  const trimmed = content.trim()
  if (trimmed.length <= 60) return trimmed || i18n.t('posts:untitledPost')
  return `${trimmed.slice(0, 57).trimEnd()}...`
}

const HASHTAG_PATTERN = /#[a-zA-Z][\w]*/g

/** Splits caption text into plain/hashtag segments for inline rendering,
 * e.g. in the Reels feed. Hashtags are a plain-text convention (no
 * dedicated backend field) parsed straight out of the caption. */
export function splitHashtags(content) {
  const segments = []
  let lastIndex = 0
  for (const match of content.matchAll(HASHTAG_PATTERN)) {
    if (match.index > lastIndex) {
      segments.push({ text: content.slice(lastIndex, match.index), isHashtag: false })
    }
    segments.push({ text: match[0], isHashtag: true })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < content.length) {
    segments.push({ text: content.slice(lastIndex), isHashtag: false })
  }
  return segments
}

export function initials(firstName, lastName, username) {
  const a = firstName?.trim().charAt(0)
  const b = lastName?.trim().charAt(0)
  if (a && b) return `${a}${b}`.toUpperCase()
  if (a) return a.toUpperCase()
  return username?.slice(0, 2).toUpperCase() ?? '?'
}

/** Compact counts for stats/metadata, e.g. 12400 -> "12.4K", 2_000_000 -> "2M". */
export function formatCount(value) {
  const n = Number(value) || 0
  if (n < 1000) return String(n)
  if (n < 1_000_000) return `${trimZero(n / 1000)}K`
  return `${trimZero(n / 1_000_000)}M`
}

function trimZero(n) {
  return n.toFixed(1).replace(/\.0$/, '')
}

/**
 * Groups a list of items into "Today" / "Yesterday" / "Earlier" buckets by a
 * date field, preserving each bucket's incoming order. Comparisons use local
 * calendar days (not a rolling 24h window), matching how activity feeds like
 * Instagram's group notifications.
 */
export function groupByDay(items, dateKey) {
  const startOfDay = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
  const today = startOfDay(new Date())
  const yesterday = today - 24 * 60 * 60 * 1000

  const buckets = { Today: [], Yesterday: [], Earlier: [] }
  for (const item of items) {
    const day = startOfDay(asUtcDate(item[dateKey]))
    if (day === today) buckets.Today.push(item)
    else if (day === yesterday) buckets.Yesterday.push(item)
    else buckets.Earlier.push(item)
  }

  return Object.entries(buckets).filter(([, list]) => list.length > 0)
}
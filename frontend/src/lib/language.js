/**
 * Lightweight Kiswahili/English detection for one narrow purpose: deciding
 * whether to show a "Translate to Kiswahili" action on an AI reply (see
 * AiConversationPage.jsx) -- "if content is already Kiswahili, do not
 * unnecessarily translate it again." This is a word-list heuristic, not a
 * real language classifier; it only has to be right often enough to avoid
 * an obviously pointless "translate" button, not perfectly accurate.
 */

// High-frequency Kiswahili function words that rarely appear in English
// text, even farming vocabulary borrowed into English sentences.
const KISWAHILI_MARKERS = new Set([
  'na', 'ya', 'wa', 'za', 'la', 'cha', 'vya', 'kwa', 'katika', 'kwenye',
  'ni', 'si', 'kwamba', 'kuwa', 'hii', 'hiyo', 'hayo', 'huu', 'huo',
  'wako', 'wangu', 'yako', 'yangu', 'lako', 'langu', 'chako', 'changu',
  'unaweza', 'utahitaji', 'tafadhali', 'karibu', 'asante', 'hakuna',
  'mkulima', 'wakulima', 'shamba', 'mazao', 'udongo', 'mbolea', 'mavuno',
  'mifugo', 'mbegu', 'wadudu', 'ugonjwa', 'kilimo', 'maji', 'mmea',
])

export function looksKiswahili(text) {
  const words = (text || '')
    .toLowerCase()
    .match(/[a-zà-ÿ']+/g)
  if (!words || words.length === 0) return false

  const hits = words.filter((word) => KISWAHILI_MARKERS.has(word)).length
  // A short threshold (2 marker words, or >12% of all words) keeps this
  // from firing on a single stray Kiswahili loanword inside an otherwise
  // English reply.
  return hits >= 2 || hits / words.length > 0.12
}

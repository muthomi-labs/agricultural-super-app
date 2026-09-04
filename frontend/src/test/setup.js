import '@testing-library/jest-dom/vitest'
import i18n from '@/i18n'

// Existing tests assert on English copy; force English regardless of
// jsdom's navigator.language or anything a previous test left in
// localStorage (i18next-browser-languagedetector caches there -- see
// src/i18n/index.js), so language never leaks across test files/runs.
i18n.changeLanguage('en')

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}

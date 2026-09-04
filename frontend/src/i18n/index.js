import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import enAdmin from './locales/en/admin.json'
import enAssistant from './locales/en/assistant.json'
import enAuth from './locales/en/auth.json'
import enCommon from './locales/en/common.json'
import enCommunities from './locales/en/communities.json'
import enExperts from './locales/en/experts.json'
import enMessaging from './locales/en/messaging.json'
import enNav from './locales/en/nav.json'
import enNotifications from './locales/en/notifications.json'
import enPosts from './locales/en/posts.json'
import enProfile from './locales/en/profile.json'
import enReels from './locales/en/reels.json'
import enSearch from './locales/en/search.json'
import enStories from './locales/en/stories.json'

import swAdmin from './locales/sw/admin.json'
import swAssistant from './locales/sw/assistant.json'
import swAuth from './locales/sw/auth.json'
import swCommon from './locales/sw/common.json'
import swCommunities from './locales/sw/communities.json'
import swExperts from './locales/sw/experts.json'
import swMessaging from './locales/sw/messaging.json'
import swNav from './locales/sw/nav.json'
import swNotifications from './locales/sw/notifications.json'
import swPosts from './locales/sw/posts.json'
import swProfile from './locales/sw/profile.json'
import swReels from './locales/sw/reels.json'
import swSearch from './locales/sw/search.json'
import swStories from './locales/sw/stories.json'

/**
 * i18n setup for the whole app. Namespaces roughly mirror feature areas
 * (see src/features/*) rather than one giant flat file, so a translator
 * (or a future contributor adding a feature) only has to look at one
 * small, relevant JSON file instead of hunting through everything.
 *
 * Language resolution order (see LanguageDetector config below):
 *   1. `asa.language` in localStorage -- set explicitly by the language
 *      switcher (see LanguageSwitcher.jsx), or synced from the
 *      authenticated user's saved preference (see LanguageSync.jsx).
 *   2. The browser's own language setting.
 *   3. "en" (SUPPORTED_LANGUAGES/fallbackLng below).
 *
 * Once a user logs in, LanguageSync.jsx takes over as the source of
 * truth (their account's User.language, from the backend) and keeps
 * this in sync with it -- see that file for why a separate effect-based
 * sync, rather than wiring this in here, keeps concerns cleanly split.
 */

export const SUPPORTED_LANGUAGES = ['en', 'sw']
export const LANGUAGE_STORAGE_KEY = 'asa.language'
export const DEFAULT_NAMESPACE = 'common'

const resources = {
  en: {
    common: enCommon,
    nav: enNav,
    auth: enAuth,
    posts: enPosts,
    stories: enStories,
    reels: enReels,
    communities: enCommunities,
    search: enSearch,
    notifications: enNotifications,
    profile: enProfile,
    assistant: enAssistant,
    admin: enAdmin,
    experts: enExperts,
    messaging: enMessaging,
  },
  sw: {
    common: swCommon,
    nav: swNav,
    auth: swAuth,
    posts: swPosts,
    stories: swStories,
    reels: swReels,
    communities: swCommunities,
    search: swSearch,
    notifications: swNotifications,
    profile: swProfile,
    assistant: swAssistant,
    admin: swAdmin,
    experts: swExperts,
    messaging: swMessaging,
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    supportedLngs: SUPPORTED_LANGUAGES,
    fallbackLng: 'en',
    ns: Object.keys(resources.en),
    defaultNS: DEFAULT_NAMESPACE,
    interpolation: {
      escapeValue: false, // React already escapes -- double-escaping would mangle output
    },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ['localStorage'],
    },
    returnEmptyString: false,
  })

export default i18n

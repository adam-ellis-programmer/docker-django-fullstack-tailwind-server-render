// simplified-ad-tracker.js - Only track start/end sessions

import {
  trackImpressionStart,
  updateImpressionDuration,
  isIntersectionObserverSupported,
} from './utils.js'

class AdImpressionTracker {
  constructor() {
    this.config = {
      impressionThreshold: 0.5, // 50% visibility required
      minimumViewTime: 1000, // 1 second minimum
      thresholds: [0, 0.25, 0.5, 0.75, 1.0],
    }

    this.observedAds = new Map()
    this.observer = null

    this.init()
  }

  // ========================================
  // INITIALIZATION
  // ========================================

  init() {
    if (!isIntersectionObserverSupported()) {
      console.warn('IntersectionObserver not supported, ad tracking disabled')
      return
    }

    this.createObserver()
    this.observeAllAds()
  }

  createObserver() {
    const options = {
      root: null,
      rootMargin: '0px',
      threshold: this.config.thresholds,
    }

    this.observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((entry) => this.handleVisibilityChange(entry)),
      options
    )
  }

  // ========================================
  // AD OBSERVATION
  // ========================================

  observeAllAds() {
    const adElements = document.querySelectorAll('[data-ad-id]')

    adElements.forEach((element) => {
      const adId = element.dataset.adId

      if (adId && !this.observedAds.has(adId)) {
        this.observer.observe(element)
        this.initializeAdData(adId, element)
      }
    })
  }

  initializeAdData(adId, element) {
    this.observedAds.set(adId, {
      element,
      impressionId: null,
      startTime: null,
      maxVisibility: 0,
      totalVisibleTime: 0,
      isVisible: false,
      impressionTracked: false,
    })
  }

  // ========================================
  // VISIBILITY HANDLING (CORE LOGIC)
  // ========================================

  handleVisibilityChange(entry) {
    const adId = entry.target.dataset.adId
    const adData = this.observedAds.get(adId)

    if (!adData) return

    // Update max visibility
    adData.maxVisibility = Math.max(
      adData.maxVisibility,
      entry.intersectionRatio
    )

    const currentlyVisible =
      entry.intersectionRatio >= this.config.impressionThreshold
    const wasVisible = adData.isVisible

    if (currentlyVisible && !wasVisible) {
      this.startAdSession(adId, adData)
    } else if (!currentlyVisible && wasVisible) {
      this.endAdSession(adId, adData)
    }
  }

  // ========================================
  // SESSION MANAGEMENT (SIMPLIFIED)
  // ========================================

  startAdSession(adId, adData) {
    adData.isVisible = true
    adData.startTime = Date.now()

    // Track impression start in database
    if (!adData.impressionTracked) {
      this.trackImpressionStart(adId, adData)
    }

    console.log(`Ad ${adId} session started`)
  }

  endAdSession(adId, adData) {
    adData.isVisible = false

    if (adData.startTime) {
      // Calculate session duration
      const sessionDuration = Date.now() - adData.startTime
      adData.totalVisibleTime += sessionDuration

      // Update database if meets minimum view time
      if (
        adData.totalVisibleTime >= this.config.minimumViewTime &&
        adData.impressionId
      ) {
        this.updateImpression(adId, adData)
      }
    }

    console.log(
      `Ad ${adId} session ended - total time: ${adData.totalVisibleTime}ms`
    )
  }

  // ========================================
  // API COMMUNICATION
  // ========================================

  async trackImpressionStart(adId, adData) {
    const response = await trackImpressionStart(adId)

    if (response?.success) {
      adData.impressionId = response.impression_id
      adData.impressionTracked = true
      console.log(
        `Impression started for ad ${adId}: ${response.impression_id}`
      )
    }
  }

  async updateImpression(adId, adData) {
    const durationSeconds = adData.totalVisibleTime / 1000
    const viewportPercentage = adData.maxVisibility

    const response = await updateImpressionDuration(
      adData.impressionId,
      durationSeconds,
      viewportPercentage
    )

    if (response?.success) {
      console.log(`Impression updated for ad ${adId}: ${durationSeconds}s`)
    }
  }
}

// ========================================
// MODULE INITIALIZATION
// ========================================

let adTracker = null

document.addEventListener('DOMContentLoaded', () => {
  adTracker = new AdImpressionTracker()
})

// Re-observe ads when new content loads (for infinite scroll)
window.addEventListener('newContentLoaded', () => {
  if (adTracker) {
    adTracker.observeAllAds()
    console.log('Re-initialized ad tracking after content load')
  }
})

// Debug export
window.getAdTrackingStats = () => {
  if (!adTracker) return null

  const stats = {
    totalAds: adTracker.observedAds.size,
    visibleAds: 0,
    trackedImpressions: 0,
  }

  adTracker.observedAds.forEach((adData) => {
    if (adData.isVisible) stats.visibleAds++
    if (adData.impressionTracked) stats.trackedImpressions++
  })

  return stats
}

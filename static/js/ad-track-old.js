// ad-impression-tracker.js - Clean, readable version

import {
  getCSRFToken,
  sendFinalImpression,
  trackImpressionStart,
  updateImpressionDuration,
  isIntersectionObserverSupported,
  calculateTrackingStats,
} from './utils.js'

class AdImpressionTracker {
  constructor() {
    this.config = {
      impressionThreshold: 0.5,    // 50% visibility required
      minimumViewTime: 1000,       // 1 second minimum
      thresholds: [0, 0.25, 0.5, 0.75, 1.0]
    }
    
    this.observedAds = new Map()
    this.observer = null
    this.isPageVisible = !document.hidden
    
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
    this.setupEventHandlers()
  }

  createObserver() {
    const options = {
      root: null,
      rootMargin: '0px',
      threshold: this.config.thresholds
    }

    this.observer = new IntersectionObserver(
      entries => entries.forEach(entry => this.handleVisibilityChange(entry)),
      options
    )
  }

  // ========================================
  // AD OBSERVATION
  // ========================================
  
  observeAllAds() {
    const adElements = document.querySelectorAll('[data-ad-id]')
    
    adElements.forEach(element => {
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
      endTime: null,
      maxVisibility: 0,
      totalVisibleTime: 0,
      isVisible: false,
      impressionTracked: false,
      updateSent: false,
      pausedTime: null
    })
  }

  // ========================================
  // VISIBILITY HANDLING (CORE LOGIC)
  // ========================================
  
  handleVisibilityChange(entry) {
    if (!this.isPageVisible) return

    const adId = entry.target.dataset.adId
    const adData = this.observedAds.get(adId)
    
    if (!adData) return

    this.updateVisibilityMetrics(adData, entry)
    
    const currentlyVisible = this.isAdVisible(entry)
    const wasVisible = adData.isVisible

    if (currentlyVisible && !wasVisible) {
      this.startAdSession(adId, adData)
    } else if (!currentlyVisible && wasVisible) {
      this.endAdSession(adId, adData)
    }
  }

  updateVisibilityMetrics(adData, entry) {
    adData.maxVisibility = Math.max(
      adData.maxVisibility,
      entry.intersectionRatio
    )
  }

  isAdVisible(entry) {
    return entry.intersectionRatio >= this.config.impressionThreshold
  }

  // ========================================
  // SESSION MANAGEMENT
  // ========================================
  
  startAdSession(adId, adData) {
    adData.isVisible = true
    adData.startTime = Date.now()

    if (!adData.impressionTracked) {
      this.trackImpressionStart(adId, adData)
    }

    console.log(`Ad ${adId} session started`)
  }

  endAdSession(adId, adData) {
    adData.isVisible = false
    adData.endTime = Date.now()

    if (adData.startTime) {
      const sessionDuration = this.calculateSessionDuration(adData)
      this.accumulateViewTime(adData, sessionDuration)
      
      this.updateImpressionIfEligible(adId, adData)
    }

    console.log(`Ad ${adId} session ended`)
  }

  calculateSessionDuration(adData) {
    return adData.endTime - adData.startTime
  }

  accumulateViewTime(adData, sessionDuration) {
    adData.totalVisibleTime += sessionDuration
  }

  updateImpressionIfEligible(adId, adData) {
    const hasMinimumViewTime = adData.totalVisibleTime >= this.config.minimumViewTime
    const notYetSent = !adData.updateSent

    if (hasMinimumViewTime && notYetSent) {
      this.updateImpression(adId, adData)
    }
  }

  // ========================================
  // API COMMUNICATION
  // ========================================
  
  async trackImpressionStart(adId, adData) {
    const response = await trackImpressionStart(adId)

    if (response?.success) {
      adData.impressionId = response.impression_id
      adData.impressionTracked = true
      console.log(`Impression started for ad ${adId}: ${response.impression_id}`)
    }
  }

  async updateImpression(adId, adData) {
    if (!adData.impressionId || adData.updateSent) return

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

  // ========================================
  // PAGE VISIBILITY HANDLING
  // ========================================
  
  setupEventHandlers() {
    document.addEventListener('visibilitychange', () => {
      this.handlePageVisibilityChange()
    })

    window.addEventListener('beforeunload', () => {
      this.handlePageUnload()
    })
  }

  handlePageVisibilityChange() {
    const wasVisible = this.isPageVisible
    this.isPageVisible = !document.hidden

    if (wasVisible && !this.isPageVisible) {
      this.pauseAllActiveSessions()
    } else if (!wasVisible && this.isPageVisible) {
      this.resumeAllActiveSessions()
    }
  }

  pauseAllActiveSessions() {
    console.log('Page hidden - pausing ad tracking')
    
    this.observedAds.forEach((adData, adId) => {
      if (this.isActiveSession(adData)) {
        this.pauseSession(adId, adData)
      }
    })
  }

  resumeAllActiveSessions() {
    console.log('Page visible - resuming ad tracking')
    
    this.observedAds.forEach((adData, adId) => {
      if (this.isPausedSession(adData)) {
        this.resumeSession(adId, adData)
      }
    })
  }

  isActiveSession(adData) {
    return adData.isVisible && adData.startTime && !adData.updateSent
  }

  isPausedSession(adData) {
    return adData.isVisible && adData.pausedTime
  }

  pauseSession(adId, adData) {
    const sessionDuration = Date.now() - adData.startTime
    
    adData.totalVisibleTime += sessionDuration
    adData.pausedTime = Date.now()

    this.updateImpressionIfEligible(adId, adData)
    
    console.log(`Paused ad ${adId} - session: ${sessionDuration}ms, total: ${adData.totalVisibleTime}ms`)
  }

  resumeSession(adId, adData) {
    adData.startTime = Date.now()
    adData.pausedTime = null
    console.log(`Resumed ad ${adId} tracking`)
  }

  // ========================================
  // PAGE UNLOAD HANDLING
  // ========================================
  
  handlePageUnload() {
    this.observedAds.forEach((adData, adId) => {
      if (this.isActiveSession(adData)) {
        this.finalizeSession(adData)
        
        if (adData.totalVisibleTime >= this.config.minimumViewTime) {
          this.sendFinalImpression(adData)
        }
      }
    })
  }

  finalizeSession(adData) {
    const sessionDuration = Date.now() - adData.startTime
    adData.totalVisibleTime += sessionDuration
  }

  sendFinalImpression(adData) {
    const durationSeconds = adData.totalVisibleTime / 1000
    
    sendFinalImpression(
      adData.impressionId,
      durationSeconds,
      adData.maxVisibility
    )
  }

  // ========================================
  // UTILITIES
  // ========================================
  
  getTrackingStats() {
    return calculateTrackingStats(
      this.observedAds,
      this.config.minimumViewTime,
      this.isPageVisible
    )
  }
}

// ========================================
// MODULE INITIALIZATION
// ========================================

let adTracker = null

document.addEventListener('DOMContentLoaded', () => {
  adTracker = new AdImpressionTracker()
})

window.addEventListener('newContentLoaded', () => {
  if (adTracker) {
    adTracker.observeAllAds()
    console.log('Re-initialized ad tracking after content load')
  }
})

// Debug export
window.getAdTrackingStats = () => adTracker?.getTrackingStats() || null
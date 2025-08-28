// static/js/ad-impression-tracking.js

class AdImpressionTracker {
  constructor() {
    this.observedAds = new Map() // Store ad viewing data
    this.impressionThreshold = 0.5 // 50% of ad must be visible
    this.minimumViewTime = 1000 // 1 second minimum for valid impression
    this.observer = null
    this.isPageVisible = !document.hidden // Track page visibility state
    this.init()
  }

  init() {
    if (!('IntersectionObserver' in window)) {
      console.warn('IntersectionObserver not supported, ad tracking disabled')
      return
    }

    this.createIntersectionObserver()
    this.observeAds()
    this.setupVisibilityHandlers()
  }

  createIntersectionObserver() {
    const options = {
      root: null, // Use viewport
      rootMargin: '0px',
      threshold: [0, 0.25, 0.5, 0.75, 1.0], // Multiple thresholds for better tracking
    }

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => this.handleAdVisibility(entry))
    }, options)
  }

  observeAds() {
    const adElements = document.querySelectorAll('[data-ad-id]')
    adElements.forEach((adEl) => {
      const adId = adEl.dataset.adId
      if (adId && !this.observedAds.has(adId)) {
        // Only if not already tracking
        this.observer.observe(adEl)

        this.observedAds.set(adId, {
          element: adEl,
          impressionId: null,
          startTime: null,
          endTime: null,
          maxVisibility: 0,
          totalVisibleTime: 0,
          isVisible: false,
          impressionTracked: false,
          updateSent: false,
          pausedTime: null, // Track when visibility was paused
        })
      }
    })
  }

  handleAdVisibility(entry) {
    // CRITICAL FIX: Don't process visibility changes if page is hidden
    if (!this.isPageVisible) {
      return
    }

    const adElement = entry.target
    const adId = adElement.dataset.adId
    const adData = this.observedAds.get(adId)

    if (!adData) return

    const isVisible = entry.intersectionRatio >= this.impressionThreshold
    const currentTime = Date.now()

    // Update max visibility percentage
    adData.maxVisibility = Math.max(
      adData.maxVisibility,
      entry.intersectionRatio
    )

    if (isVisible && !adData.isVisible) {
      // Ad became visible
      adData.isVisible = true
      adData.startTime = currentTime

      // Track impression start
      if (!adData.impressionTracked) {
        this.trackImpressionStart(adId, adData)
      }

      console.log(
        `Ad ${adId} became visible (${Math.round(
          entry.intersectionRatio * 100
        )}%)`
      )
    } else if (!isVisible && adData.isVisible) {
      // Ad became invisible
      adData.isVisible = false
      adData.endTime = currentTime

      if (adData.startTime) {
        const viewDuration = currentTime - adData.startTime
        adData.totalVisibleTime += viewDuration

        // Send update if viewed long enough
        if (
          adData.totalVisibleTime >= this.minimumViewTime &&
          !adData.updateSent
        ) {
          this.updateImpressionDuration(adId, adData)
        }
      }

      console.log(
        `Ad ${adId} became invisible after ${adData.totalVisibleTime}ms total view time`
      )
    }
  }

  setupVisibilityHandlers() {
    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
      this.handleVisibilityChange()
    })

    // Handle page unload
    window.addEventListener('beforeunload', () => {
      this.handleBeforeUnload()
    })
  }

  // Handle page visibility changes
  handleVisibilityChange() {
    const wasVisible = this.isPageVisible
    this.isPageVisible = !document.hidden

    if (wasVisible && !this.isPageVisible) {
      // Page became hidden - pause all visible ads
      console.log('Page became hidden - pausing ad tracking')
      this.pauseAllVisibleAds()
    } else if (!wasVisible && this.isPageVisible) {
      // Page became visible - resume tracking for visible ads
      console.log('Page became visible - resuming ad tracking')
      this.resumeVisibleAds()
    }
  }

  pauseAllVisibleAds() {
    const currentTime = Date.now()
    
    this.observedAds.forEach((adData, adId) => {
      if (adData.isVisible && adData.startTime && !adData.updateSent) {
        // Calculate and add the current session duration
        const sessionDuration = currentTime - adData.startTime
        adData.totalVisibleTime += sessionDuration
        adData.pausedTime = currentTime

        // Send update if we've reached minimum view time
        if (adData.totalVisibleTime >= this.minimumViewTime) {
          this.updateImpressionDuration(adId, adData)
        }

        console.log(`Paused ad ${adId} after ${sessionDuration}ms session (${adData.totalVisibleTime}ms total)`)
      }
    })
  }

  resumeVisibleAds() {
    const currentTime = Date.now()
    
    this.observedAds.forEach((adData, adId) => {
      if (adData.isVisible && adData.pausedTime) {
        // Resume timing from current time
        adData.startTime = currentTime
        adData.pausedTime = null
        console.log(`Resumed ad ${adId} tracking`)
      }
    })
  }

  async trackImpressionStart(adId, adData) {
    try {
      const response = await fetch('/feed/api/track-ad-impression/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken(),
        },
        body: JSON.stringify({ ad_id: adId }),
      })

      const data = await response.json()

      if (data.success) {
        adData.impressionId = data.impression_id
        adData.impressionTracked = true
        console.log(
          `Tracked impression start for ad ${adId}: ${data.impression_id}`
        )
      } else {
        console.log(
          `Impression tracking response for ad ${adId}:`,
          data.message
        )
      }
    } catch (error) {
      console.error(`Failed to track impression for ad ${adId}:`, error)
    }
  }

  async updateImpressionDuration(adId, adData) {
    if (!adData.impressionId || adData.updateSent) {
      return
    }

    try {
      const durationSeconds = adData.totalVisibleTime / 1000
      const viewportPercentage = adData.maxVisibility

      const response = await fetch('/feed/api/update-ad-impression/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken(),
        },
        body: JSON.stringify({
          impression_id: adData.impressionId,
          duration_seconds: durationSeconds,
          viewport_percentage: viewportPercentage,
        }),
      })

      const data = await response.json()

      if (data.success) {
        // Don't mark as sent yet - allow for future updates if user returns
        console.log(
          `Updated impression duration for ad ${adId}: ${durationSeconds}s`
        )
      }
    } catch (error) {
      console.error(
        `Failed to update impression duration for ad ${adId}:`,
        error
      )
    }
  }

  getCSRFToken() {
    // Try to get from hidden input first
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]')
    if (csrfInput) {
      return csrfInput.value
    }

    // Fallback to cookie method
    const name = 'csrftoken'
    let cookieValue = null
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';')
      for (let cookie of cookies) {
        const cleanCookie = cookie.trim()
        if (cleanCookie.substring(0, name.length + 1) === name + '=') {
          cookieValue = decodeURIComponent(
            cleanCookie.substring(name.length + 1)
          )
          break
        }
      }
    }
    return cookieValue
  }

  // Handle page unload
  handleBeforeUnload() {
    // Send final updates for any visible ads
    this.observedAds.forEach((adData, adId) => {
      if (adData.isVisible && adData.startTime && !adData.updateSent) {
        const currentTime = Date.now()
        const viewDuration = currentTime - adData.startTime
        adData.totalVisibleTime += viewDuration

        if (adData.totalVisibleTime >= this.minimumViewTime) {
          // Use sendBeacon for reliable final tracking
          this.sendFinalImpression(adId, adData)
        }
      }
    })
  }

  sendFinalImpression(adId, adData) {
    if (!adData.impressionId) return

    const durationSeconds = adData.totalVisibleTime / 1000
    const data = JSON.stringify({
      impression_id: adData.impressionId,
      duration_seconds: durationSeconds,
      viewport_percentage: adData.maxVisibility,
    })

    // Use sendBeacon for reliable tracking on page unload
    if (navigator.sendBeacon) {
      const blob = new Blob([data], { type: 'application/json' })
      navigator.sendBeacon('/feed/api/update-ad-impression/', blob)
    }
  }

  // Get current tracking statistics (for debugging)
  getTrackingStats() {
    const stats = {
      totalAds: this.observedAds.size,
      visibleAds: 0,
      trackedImpressions: 0,
      validImpressions: 0,
      isPageVisible: this.isPageVisible,
    }

    this.observedAds.forEach((adData, adId) => {
      if (adData.isVisible) stats.visibleAds++
      if (adData.impressionTracked) stats.trackedImpressions++
      if (adData.totalVisibleTime >= this.minimumViewTime)
        stats.validImpressions++
    })

    return stats
  }
}

// Initialize ad impression tracking when DOM is ready
let adTracker = null

document.addEventListener('DOMContentLoaded', function () {
  adTracker = new AdImpressionTracker()
})

// Re-observe ads after infinite scroll loads new content
window.addEventListener('newContentLoaded', function () {
  if (adTracker) {
    adTracker.observeAds()
    console.log('Re-initialized ad tracking after content load')
  }
})

// Export for debugging
window.getAdTrackingStats = () => {
  return adTracker ? adTracker.getTrackingStats() : null
}
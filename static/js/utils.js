// utils.js - Ad Tracking Utilities

/**
 * Get CSRF token for Django AJAX requests
 * @returns {string|null} CSRF token or null if not found
 */
export function getCSRFToken() {
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
        cookieValue = decodeURIComponent(cleanCookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

/**
 * Send final impression data using sendBeacon for reliable tracking on page unload
 * @param {string} impressionId - The impression ID to update
 * @param {number} durationSeconds - Total view duration in seconds
 * @param {number} viewportPercentage - Maximum viewport percentage visible
 */
export function sendFinalImpression(
  impressionId,
  durationSeconds,
  viewportPercentage
) {
  if (!impressionId) return

  const data = JSON.stringify({
    impression_id: impressionId,
    duration_seconds: durationSeconds,
    viewport_percentage: viewportPercentage,
  })

  // Use sendBeacon for reliable tracking on page unload
  if (navigator.sendBeacon) {
    const blob = new Blob([data], { type: 'application/json' })
    navigator.sendBeacon('/feed/api/update-ad-impression/', blob)
  }
}

/**
 * Make API request to track ad impression start
 * @param {string} adId - Advertisement ID
 * @returns {Promise<Object|null>} Response data or null if failed
 */
export async function trackImpressionStart(adId) {
  try {
    const response = await fetch('/feed/api/track-ad-impression/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ ad_id: adId }),
    })

    const data = await response.json()
    return data
  } catch (error) {
    console.error(`Failed to track impression for ad ${adId}:`, error)
    return null
  }
}

/**
 * Make API request to update ad impression duration
 * @param {string} impressionId - Database impression ID
 * @param {number} durationSeconds - Total view duration in seconds
 * @param {number} viewportPercentage - Maximum viewport percentage visible
 * @returns {Promise<Object|null>} Response data or null if failed
 */
export async function updateImpressionDuration(
  impressionId,
  durationSeconds,
  viewportPercentage
) {
  try {
    const response = await fetch('/feed/api/update-ad-impression/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({
        impression_id: impressionId,
        duration_seconds: durationSeconds,
        viewport_percentage: viewportPercentage,
      }),
    })

    const data = await response.json()
    return data
  } catch (error) {
    console.error(`Failed to update impression duration:`, error)
    return null
  }
}

/**
 * Check if IntersectionObserver is supported in current browser
 * @returns {boolean} True if supported
 */
export function isIntersectionObserverSupported() {
  return 'IntersectionObserver' in window
}

/**
 * Calculate statistics from observed ads Map
 * @param {Map} observedAds - Map of ad tracking data
 * @param {number} minimumViewTime - Minimum time for valid impression
 * @param {boolean} isPageVisible - Current page visibility state
 * @returns {Object} Statistics object
 */
export function calculateTrackingStats(
  observedAds,
  minimumViewTime,
  isPageVisible
) {
  const stats = {
    totalAds: observedAds.size,
    visibleAds: 0,
    trackedImpressions: 0,
    validImpressions: 0,
    isPageVisible: isPageVisible,
  }

  observedAds.forEach((adData, adId) => {
    if (adData.isVisible) stats.visibleAds++
    if (adData.impressionTracked) stats.trackedImpressions++
    if (adData.totalVisibleTime >= minimumViewTime) stats.validImpressions++
  })

  return stats
}

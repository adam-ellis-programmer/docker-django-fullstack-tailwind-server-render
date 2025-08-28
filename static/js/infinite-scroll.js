// static/js/infinite-scroll.js

// Infinite Scroll Implementation using Functions
let currentPage = 1
let hasNextPage = true
let isLoading = false
let apiEndpoint = '/feed/api/load-more-posts/' // Default endpoint

// Initialize infinite scroll with configuration
function initInfiniteScroll(config = {}) {
  currentPage = config.nextPage || 1
  hasNextPage = config.hasNext !== undefined ? config.hasNext : true
  apiEndpoint = config.endpoint || '/feed/api/load-more-posts/'

  initializeInfiniteScroll()
}

// Get CSRF token for AJAX requests
function getCSRFToken() {
  // Try to get from hidden input first (Django {% csrf_token %})
  const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]')
  if (csrfInput) {
    return csrfInput.value
  }

  // Fallback to cookie method
  const name = 'csrftoken'
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

// Create and configure Intersection Observer
function createIntersectionObserver() {
  const options = {
    root: null, // Use viewport as root
    rootMargin: '-100px', // Start loading 100px before element is visible
    threshold: 0.8, // Trigger when 10% of element is visible
  }

  // Element that the obserever is on (scroll-trigger) in posts_feed.html
  const observer = new IntersectionObserver(handleIntersection, options)
  const trigger = document.getElementById('scroll-trigger')

  if (trigger) {
    observer.observe(trigger)
  }

  return observer
}

// Handle intersection observer callback
function handleIntersection(entries, observer) {
  entries.forEach((entry) => {
    if (entry.isIntersecting && !isLoading && hasNextPage) {
      loadMorePosts()
    }
  })
}

// Load more posts function
async function loadMorePosts() {
  if (isLoading || !hasNextPage) {
    return
  }

  isLoading = true
  showLoadingIndicator()

  try {
    // Add minimum delay to see loading indicator
    const [response] = await Promise.all([
      fetch(`${apiEndpoint}?page=${currentPage}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCSRFToken(),
        },
      }),
      // for development only
      new Promise((resolve) => setTimeout(resolve, 500)), // 500ms minimum
    ])

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()

    if (data.html) {
      // -- HTML --
      // console.log(data.html)
      appendPosts(data.html)
      // CRITICAL: Tell ad tracker about new content
      window.dispatchEvent(new CustomEvent('newContentLoaded'))
      currentPage = data.next_page || currentPage + 1
      hasNextPage = data.has_next

      if (!hasNextPage) {
        showEndOfPosts()
      }
    }
  } catch (error) {
    console.error('Error loading more posts:', error)
    showLoadMoreButton()
  } finally {
    isLoading = false
    hideLoadingIndicator()
  }
}

// Append new posts to the container
function appendPosts(html) {
  const container = document.getElementById('posts-container')
  if (!container) {
    console.error('Posts container not found')
    return
  }

  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html

  // Append each post with animation
  Array.from(tempDiv.children).forEach((post, index) => {
    post.style.opacity = '0'
    post.style.transform = 'translateY(20px)'
    container.appendChild(post)

    // Animate post appearance
    setTimeout(() => {
      post.style.transition = 'opacity 0.3s ease, transform 0.3s ease'
      post.style.opacity = '1'
      post.style.transform = 'translateY(0)'
    }, index * 50) // Stagger animation
  })
}

// Show loading indicator
function showLoadingIndicator() {
  const indicator = document.getElementById('loading-indicator')
  if (indicator) {
    indicator.classList.remove('hidden')
  }
}

// Hide loading indicator
function hideLoadingIndicator() {
  const indicator = document.getElementById('loading-indicator')
  if (indicator) {
    indicator.classList.add('hidden')
  }
}

// Show end of posts message
function showEndOfPosts() {
  const endMessage = document.getElementById('end-of-posts')
  const trigger = document.getElementById('scroll-trigger')

  if (endMessage) {
    endMessage.classList.remove('hidden')
  }

  // Hide the intersection trigger
  if (trigger) {
    trigger.style.display = 'none'
  }
}

// Show load more button (fallback)
function showLoadMoreButton() {
  const button = document.getElementById('load-more-button')
  if (button) {
    button.style.display = 'block'
  }
}

// Initialize intersection observer when page loads
function initializeInfiniteScroll() {
  // Check if we're on a page that needs infinite scroll
  const postsContainer = document.getElementById('posts-container')
  if (!postsContainer) {
    return // Exit if not on a posts page
  }

  // Check if Intersection Observer is supported
  if ('IntersectionObserver' in window) {
    createIntersectionObserver()
  } else {
    // Fallback for older browsers
    console.warn(
      'Intersection Observer not supported, falling back to load more button'
    )
    showLoadMoreButton()
  }
}

// Throttled scroll handler as additional fallback
// function handleScroll() {
//   const scrollPosition = window.innerHeight + window.scrollY
//   const documentHeight = document.documentElement.offsetHeight

//   if (scrollPosition >= documentHeight - 1000 && !isLoading && hasNextPage) {
//     loadMorePosts()
//   }
// }

// Debounce function for scroll events
// function debounce(func, wait) {
//   let timeout
//   return function executedFunction(...args) {
//     const later = () => {
//       clearTimeout(timeout)
//       func(...args)
//     }
//     clearTimeout(timeout)
//     timeout = setTimeout(later, wait)
//   }
// }

// Handle page visibility changes
function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    // Reset any stuck loading states when user returns to page
    isLoading = false
    hideLoadingIndicator()
  }
}

// Auto-initialize when DOM is ready (only if not manually initialized)
// Update the auto-initialization section in infinite-scroll.js
document.addEventListener('DOMContentLoaded', function () {
  const infiniteScrollElement = document.querySelector(
    '[data-infinite-scroll="true"]'
  )

  if (infiniteScrollElement && !window.infiniteScrollInitialized) {
    const config = {
      nextPage:
        infiniteScrollElement.dataset.nextPage !== 'null'
          ? parseInt(infiniteScrollElement.dataset.nextPage)
          : null,
      hasNext: infiniteScrollElement.dataset.hasNext === 'true',
      endpoint: infiniteScrollElement.dataset.endpoint,
    }

    initInfiniteScroll(config)
    window.infiniteScrollInitialized = true
  }
})

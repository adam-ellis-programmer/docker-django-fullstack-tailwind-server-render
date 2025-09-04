// Optimized post-likes.js with better error handling and UI feedback

// Track pending requests to prevent double-clicks
const pendingLikes = new Set()

document.addEventListener('DOMContentLoaded', function () {
  // Use event delegation for better performance with infinite scroll
  document.addEventListener('click', function (e) {
    const likeButton = e.target.closest('.like-button')
    if (likeButton) {
      e.preventDefault()
      handleLikeClick(likeButton)
    }
  })
})

async function handleLikeClick(button) {
  const postId = button.dataset.postId

  // Prevent double-clicks
  if (pendingLikes.has(postId)) {
    return
  }

  // Add visual feedback immediately
  const heartIcon = button.querySelector('i')
  const likeCount = button.querySelector('.like-count')

  // Store original states for rollback
  const originalHeartClass = heartIcon.className
  const originalButtonClass = button.className
  const originalCount = parseInt(likeCount.textContent)

  // Optimistic UI update
  const isCurrentlyLiked = heartIcon.classList.contains('fa-solid')
  const newCount = isCurrentlyLiked ? originalCount - 1 : originalCount + 1

  // Update UI immediately
  updateLikeButtonUI(button, !isCurrentlyLiked, newCount)

  // Add to pending set
  pendingLikes.add(postId)

  try {
    // Make the API request with timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout

    const response = await fetch('/feed/toggle-like/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify({ post_id: postId }),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    
    const data = await response.json()
    console.log('POST LIKE RESPONSE', data)

    if (data.success) {
      // Update UI with server response
      updateLikeButtonUI(button, data.user_has_liked, data.new_like_count)

      // Show success feedback (optional)
      showFeedback(button, 'success')
    } else {
      throw new Error(data.error || 'Unknown error occurred')
    }
  } catch (error) {
    console.error('Like toggle error:', error)

    // Rollback optimistic update
    heartIcon.className = originalHeartClass
    button.className = originalButtonClass
    likeCount.textContent = originalCount

    // Show error feedback
    showFeedback(button, 'error')

    // User-friendly error message
    if (error.name === 'AbortError') {
      console.warn('Like request timed out')
    } else {
      console.warn('Failed to update like. Please try again.')
    }
  } finally {
    // Remove from pending set
    pendingLikes.delete(postId)
  }
}

function updateLikeButtonUI(button, isLiked, count) {
  const heartIcon = button.querySelector('i')
  const likeCount = button.querySelector('.like-count')

  if (isLiked) {
    // User likes the post
    heartIcon.className = 'fa-solid fa-heart text-red-500'
    button.className = button.className.replace(
      'text-gray-500 hover:text-red-500',
      'text-red-500'
    )
  } else {
    // User doesn't like the post
    heartIcon.className = 'fa-regular fa-heart'
    button.className = button.className.replace(
      'text-red-500',
      'text-gray-500 hover:text-red-500'
    )
  }

  likeCount.textContent = count
}

function showFeedback(button, type) {
  // Add a subtle animation to show the action completed
  const icon = button.querySelector('i')

  if (type === 'success') {
    icon.style.transform = 'scale(1.2)'
    setTimeout(() => {
      icon.style.transform = 'scale(1)'
    }, 150)
  } else if (type === 'error') {
    button.style.transform = 'translateX(-2px)'
    setTimeout(() => {
      button.style.transform = 'translateX(2px)'
    }, 100)
    setTimeout(() => {
      button.style.transform = 'translateX(0)'
    }, 200)
  }
}

function getCSRFToken() {
  // Try hidden input first
  const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]')
  if (csrfInput) {
    return csrfInput.value
  }

  // Fallback to cookie
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

// console.log('Post likes functionality loaded!')

// Get CSRF token from Django
function getCSRFToken() {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')
  if (csrfToken) {
    return csrfToken.value
  }

  // Fallback: get from cookie
  const name = 'csrftoken'
  const cookies = document.cookie.split(';')
  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split('=')
    if (key === name) {
      return decodeURIComponent(value)
    }
  }
  return null
}

// JavaScript for Conditional Rendering (Replace Heart Icon)
function handleLikeClick(postId, likeButton) {
  if (likeButton.classList.contains('processing')) return

  likeButton.classList.add('processing')
  likeButton.style.pointerEvents = 'none' // Prevent additional clicks

  const likeCountSpan = likeButton.querySelector('.like-count')
  const currentCount = parseInt(likeCountSpan.textContent)
  let heartIcon = likeButton.querySelector('.fa-heart')

  // Check current state
  const isCurrentlyLiked = heartIcon.classList.contains('fa-solid')

  console.log(
    `Post ${postId} - Currently liked: ${isCurrentlyLiked}, Current count: ${currentCount}`
  )

  // 2. Optimistic update (immediate UI change)
  if (isCurrentlyLiked) {
    // Unlike - replace with empty heart
    likeCountSpan.textContent = currentCount - 1
    heartIcon.className = 'fa-regular fa-heart' // Unlike
    // likeButton.classList.remove('text-red-500')
    // likeButton.classList.add('text-gray-500')
    console.log('Optimistically unliked')
  } else {
    // Like - replace with filled heart
    likeCountSpan.textContent = currentCount + 1
    heartIcon.className = 'fa-solid fa-heart text-red-500' // Unlike
    // likeButton.classList.remove('text-gray-500')
    // likeButton.classList.add('text-red-500')
    console.log('Optimistically liked')
  }

  // API call
  fetch('/feed/toggle-like/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
    },
    body: JSON.stringify({ post_id: postId }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      console.log('Server response:', data)

      if (data.success) {
        likeCountSpan.textContent = data.new_like_count

        // Update heart based on server response
        heartIcon = likeButton.querySelector('.fa-heart') // Re-get reference
        if (data.user_has_liked) {
          heartIcon.className = 'fa-solid fa-heart text-red-500'
          likeButton.classList.add('text-red-500')
          likeButton.classList.remove('text-gray-500')
        } else {
          heartIcon.className = 'fa-regular fa-heart'
          likeButton.classList.add('text-gray-500')
          likeButton.classList.remove('text-red-500')
        }

        console.log(
          `Post ${postId} ${data.action}! Server count: ${data.new_like_count}`
        )
      } else {
        console.error('Error from server:', data.error)
        // Revert on error
        likeCountSpan.textContent = currentCount
        if (isCurrentlyLiked) {
          heartIcon.className = 'fa-solid fa-heart text-red-500'
          likeButton.classList.add('text-red-500')
          likeButton.classList.remove('text-gray-500')
        } else {
          heartIcon.className = 'fa-regular fa-heart'
          likeButton.classList.add('text-gray-500')
          likeButton.classList.remove('text-red-500')
        }
      }
    })
    .catch((error) => {
      console.error('Network error:', error)
      // Revert on network error
      likeCountSpan.textContent = currentCount
      if (isCurrentlyLiked) {
        heartIcon.className = 'fa-solid fa-heart text-red-500'
        likeButton.classList.add('text-red-500')
        likeButton.classList.remove('text-gray-500')
      } else {
        heartIcon.className = 'fa-regular fa-heart'
        likeButton.classList.add('text-gray-500')
        likeButton.classList.remove('text-red-500')
      }
    })
    .finally(() => {
      // Re-enable button
      likeButton.classList.remove('processing')
      likeButton.style.pointerEvents = 'auto'
    })
}

// Initialize like functionality with event delegation
function initializeLikeButtons() {
  // console.log('Setting up like button listeners...')

  // Use event delegation for dynamically loaded content
  document.addEventListener('click', function (event) {
    const likeButton = event.target.closest('.like-button')
    if (!likeButton) return

    event.preventDefault()
    event.stopPropagation()

    const postId = likeButton.dataset.postId
    if (!postId) {
      console.error('No post ID found on like button')
      return
    }

    console.log(`Like button clicked for post ${postId}`)
    handleLikeClick(postId, likeButton)
  })

  // console.log('Like button listeners ready!')
}

// Set up event listeners when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeLikeButtons)
} else {
  // DOM is already loaded
  initializeLikeButtons()
}

// current setup uses event delegation.
// Also initialize after dynamic content loads (for infinite scroll)
// window.reinitializeLikeButtons = initializeLikeButtons;

// -------------------------------------------------------------------
// When you WOULD need window.reinitializeLikeButtons:
// If you were using direct event binding instead:
// -------------------------------------------------------------------

// This approach would need reinitialization
// document.querySelectorAll('.like-button').forEach(button => {
//     button.addEventListener('click', handleLikeClick);
// });
// New buttons loaded later wouldn't have listeners!

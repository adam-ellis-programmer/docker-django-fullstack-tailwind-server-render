// modal.js - Simple modal system with automatic event delegation

/**
 * Show modal with dynamic content
 */

function showModal(content) {
  const modal = document.getElementById('modal-overlay')
  const modalContent = document.getElementById('modal-content')

  if (!modal || !modalContent) {
    console.error('Modal elements not found in DOM')
    return
  }

  modalContent.innerHTML = content // Inject dynamic HTML
  modal.classList.remove('hidden') // Make modal visible
  document.body.classList.add('overflow-hidden') // Prevent scrolling
}

/**
 * Close the modal
 */
function closeModal() {
  const modal = document.getElementById('modal-overlay')
  if (modal) {
    modal.classList.add('hidden')
    document.body.classList.remove('overflow-hidden')
  }
}

/**
 * Show delete confirmation modal
 */
function confirmDeletePost(postId, postTitle) {
  console.log('Delete modal triggered for post:', postId)

  const content = `
    <div class="p-6">
      <div class="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
        <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-gray-900 text-center mb-2">Delete Post</h3>
      <p class="text-sm text-gray-600 text-center mb-6">
        Are you sure you want to delete "<strong>${escapeHtml(
          postTitle
        )}</strong>"? This action cannot be undone.
      </p>
      <div class="flex space-x-3">
        <button 
          class="modal-close-btn flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
        >
          Cancel
        </button>
        <button 
          class="confirm-delete-btn flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
          data-post-id="${postId}"
        >
          Delete Post
        </button>
      </div>
    </div>
  `

  showModal(content)
}

/**
 * Show edit form modal
 */
function showEditPostModal(postId, currentTitle, currentText, currentLocation) {
  console.log('Edit modal triggered for post:', postId)

  const content = `
    <div class="p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900">Edit Post</h3>
        <button class="modal-close-btn text-gray-400 hover:text-gray-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <form id="edit-post-form" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <input 
            type="text" 
            id="edit-title" 
            value="${escapeHtml(currentTitle)}"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Content</label>
          <textarea 
            id="edit-text" 
            rows="4"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          >${escapeHtml(currentText)}</textarea>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Location</label>
          <input 
            type="text" 
            id="edit-location" 
            value="${escapeHtml(currentLocation)}"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        
        <div class="flex space-x-3 pt-4">
          <button 
            type="button"
            class="modal-close-btn flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
          >
            Cancel
          </button>
          <button 
            type="submit"
            class="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
          >
            Save Changes
          </button>
        </div>
      </form>
    </div>
  `

  showModal(content)
}

/**
 * Delete a post
 */
async function deletePost(postId) {
  console.log('Deleting post:', postId)

  try {
    const response = await fetch(`/feed/post/${postId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': window.getCSRFToken(),
        'Content-Type': 'application/json',
      },
    })

    if (response.ok) {
      closeModal()
      // Remove the post from DOM with animation
      const postElement = document.querySelector(`[data-post-id="${postId}"]`)
      if (postElement) {
        postElement.style.opacity = '0'
        postElement.style.transform = 'translateY(-10px)'
        postElement.style.transition = 'all 0.3s ease-out'
        setTimeout(() => postElement.remove(), 300)
      }

      showSuccessMessage('Post deleted successfully')
    } else {
      throw new Error('Failed to delete post')
    }
  } catch (error) {
    console.error('Error deleting post:', error)
    showErrorModal('Failed to delete the post. Please try again.')
  }
}

/**
 * Update a post
 */
async function updatePost(postId, data) {
  console.log('Updating post:', postId, data)

  try {
    const response = await fetch(`/feed/post/${postId}/edit/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': window.getCSRFToken(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (response.ok) {
      closeModal()
      showSuccessMessage('Post updated successfully')
      // Reload the page to show updated content
      setTimeout(() => window.location.reload(), 1000)
    } else {
      throw new Error('Failed to update post')
    }
  } catch (error) {
    console.error('Error updating post:', error)
    showErrorModal('Failed to update the post. Please try again.')
  }
}

/**
 * Show error modal
 */
function showErrorModal(message) {
  const content = `
    <div class="p-6 text-center">
      <div class="w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
        <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-gray-900 mb-2">Error</h3>
      <p class="text-sm text-gray-600 mb-4">${escapeHtml(message)}--</p>
      <button 
        class="modal-close-btn px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
      >
        Close
      </button>
    </div>
  `
  showModal(content)
}

/**
 * Show success message (toast-style)
 */
function showSuccessMessage(message) {
  const toast = document.createElement('div')
  toast.className =
    'fixed top-4 right-4 z-60 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg transform translate-x-full transition-transform duration-300'
  toast.textContent = message

  document.body.appendChild(toast)

  // Animate in
  setTimeout(() => {
    toast.classList.remove('translate-x-full')
  }, 100)

  // Remove after 3 seconds
  setTimeout(() => {
    toast.classList.add('translate-x-full')
    setTimeout(() => toast.remove(), 300)
  }, 3000)
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// ============================================
// AUTO-INITIALIZE EVENT LISTENERS
// ============================================

// Close modal on Escape key
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    closeModal()
  }
})

// Close modal when clicking backdrop
document.addEventListener('click', function (e) {
  const modalOverlay = document.getElementById('modal-overlay')
  if (e.target === modalOverlay) {
    closeModal()
  }
})

// // Single listener for ALL edit buttons
// Event delegation for edit buttons
document.addEventListener('click', function (e) {
  if (e.target.closest('.edit-post-btn')) {
    console.log('Edit button clicked')
    e.preventDefault()
    const button = e.target.closest('.edit-post-btn')
    const postId = button.dataset.postId
    const postTitle = button.dataset.postTitle
    const postText = button.dataset.postText
    const postLocation = button.dataset.postLocation

    showEditPostModal(postId, postTitle, postText, postLocation)
  }
})

// Event delegation for delete buttons
document.addEventListener('click', function (e) {
  if (e.target.closest('.delete-post-btn')) {
    console.log('Delete button clicked')
    e.preventDefault()
    const button = e.target.closest('.delete-post-btn')
    const postId = button.dataset.postId
    const postTitle = button.dataset.postTitle

    confirmDeletePost(postId, postTitle)
  }
})

// Event delegation for modal close buttons
document.addEventListener('click', function (e) {
  if (e.target.closest('.modal-close-btn')) {
    console.log('Modal close button clicked')
    closeModal()
  }
})

// Event delegation for confirm delete buttons
document.addEventListener('click', function (e) {
  if (e.target.closest('.confirm-delete-btn')) {
    console.log('Confirm delete clicked')
    const button = e.target.closest('.confirm-delete-btn')
    const postId = button.dataset.postId
    deletePost(postId)
  }
})

// Event delegation for edit form submissions
document.addEventListener('submit', function (e) {
  if (e.target.id === 'edit-post-form') {
    console.log('Edit form submitted')
    e.preventDefault()

    // Get the post ID from the form's context
    const modal = document.getElementById('modal-content')
    const editBtn = document.querySelector('.edit-post-btn[data-post-id]')
    const postId = editBtn ? editBtn.dataset.postId : null

    if (postId) {
      // Get values using getElementById
      const title = document.getElementById('edit-title').value
      const text = document.getElementById('edit-text').value
      const location = document.getElementById('edit-location').value

      updatePost(postId, { title, text, location })
    }
  }
})

// console.log('Modal system loaded - event listeners active')

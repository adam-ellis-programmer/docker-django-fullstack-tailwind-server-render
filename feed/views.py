from django.shortcuts import render
# from datetime import datetime, timedelta

from feed.data import temp_posts

import random

# Create your views here.

def public_posts(request):
    # Sort posts by timestamp (most recent first)
    sorted_posts = sorted(
        temp_posts, key=lambda x: x['timestamp'], reverse=True)

    context = {
        'posts': sorted_posts,
        'total_posts': len(sorted_posts)
    }

    return render(request, 'public-posts.html', context)

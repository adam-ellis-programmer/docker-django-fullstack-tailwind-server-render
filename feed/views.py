from django.shortcuts import render

# Create your views here.


def public_posts(request):
    return render(request, 'public-posts.html')

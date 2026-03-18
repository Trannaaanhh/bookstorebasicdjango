from django.shortcuts import render
from django.db.models import Q
from store.models import Book
from store.utils.demo_classes import RecommendationEngine

recommendation_engine = RecommendationEngine()


def list_books(request):
    query = request.GET.get('q')
    books = Book.objects.all()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    context = {
        'books': books,
        'query': query or ''
    }
    return render(request, 'book/list.html', context)


def book_detail(request, pk):
    book = Book.objects.get(pk=pk)
    recommendations = recommendation_engine.recommend(pk, limit=4)
    context = {
        'book': book,
        'recommendations': recommendations
    }
    return render(request, 'book/detail.html', context)

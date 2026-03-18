from django.urls import path
from store.controllers import bookController

urlpatterns = [
    path('', bookController.list_books, name='book_list'),
    path('<int:pk>/', bookController.book_detail, name='book_detail'),
]
from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100) # Thực tế nên dùng AbstractUser của Django

    def __str__(self):
        return self.name
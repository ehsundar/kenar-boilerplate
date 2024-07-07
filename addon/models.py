from django.db import models


class Post(models.Model):
    token = models.CharField(max_length=50)


class DivarUsers(models.Model):
    phone = models.CharField(max_length=11, primary_key=True)


class Product(models.Model):
    owner = models.ForeignKey(DivarUsers, on_delete=models.CASCADE)

    name = models.CharField(max_length=50, null=False, blank=False)
    price = models.IntegerField(null=False, blank=False)
    content = models.FileField(upload_to='products/', null=False, blank=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

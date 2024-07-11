from django.db import models


class Post(models.Model):
    token = models.CharField(max_length=50)


class DivarUsers(models.Model):
    phone = models.CharField(max_length=11, primary_key=True)


class Product(models.Model):
    post_token = models.CharField(max_length=9, primary_key=True)
    owner = models.ForeignKey(DivarUsers, on_delete=models.CASCADE)

    name = models.CharField(max_length=50)
    price = models.IntegerField()
    content = models.FileField(upload_to='products/')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

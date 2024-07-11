from django.urls import path

from . import views

urlpatterns = [
    path("", views.LandingView.as_view(), name="addon.landing"),
    path("addon_oauth/", views.addon_oauth, name="addon.manage.start_oauth"),
    path("oauth_callback/", views.addon_app, name="addon.oauth_callback"),
    path("upload/", views.CreateProductView.as_view(), name="product_create"),
    path("thanks/", views.AppClose.as_view(), name="app_close"),
    path("buy/<int:product_id>", views.BuyProductView.as_view(), name="addon.product.buy"),
    path("buy/<int:product_id>/demo", views.ProductDemoView.as_view(), name="addon.product.demo"),
]

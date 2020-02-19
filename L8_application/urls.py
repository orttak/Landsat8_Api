from L8_application import views
from django.urls import path
from django.conf.urls import url,include
from rest_framework.routers import DefaultRouter

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'landsat', views.Landsat8List)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    url('', include(router.urls)),
    path('landsat2/',views.LandsatPostView.as_view(),name='landsat2'),
    path('landsat3/',views.LandsatNdviView.as_view(),name='landsat3'),
]


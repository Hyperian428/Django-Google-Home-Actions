# myapp/urls.py
from django.conf.urls import include, url
from . import views

urlpatterns = [
    url('dashboard', views.dashboard),
    url('logout', views.logout),
    url('', include('django.contrib.auth.urls')),
    url('', include('social_django.urls')),
    url('', views.home, name='home'),   
]
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^switch$', views.switch, name='switch'),
]
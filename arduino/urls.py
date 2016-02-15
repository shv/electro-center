from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^status$', views.switch, name='status'),
    url(r'^switch$', views.switch, name='switch'),
]
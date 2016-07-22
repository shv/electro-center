"""ihome URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin
from arduino.views import switch, status, dim
from mainframe.views import communicate, get, post


urlpatterns = [
    url(r'^arduino/', include('arduino.urls')),
    url(r'^mainframe/', include('mainframe.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^switch', switch),
    url(r'^dim', dim),
    url(r'^status', status),
    url(r'^api/v0.1/communicate/(?P<token>[a-z0-9\-]+)$', communicate, name='communicate'),
    url(r'^api/v0.1/post/(?P<token>[a-z0-9\-]+)$', post, name='post'),
    url(r'^api/v0.1/get/(?P<token>[a-z0-9\-]+)$', get, name='get'),
]


from django.conf.urls import patterns, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('django_sec.tests.views',
    (r'^admin/', include(admin.site.urls)),
)

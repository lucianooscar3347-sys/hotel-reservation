from django.contrib import admin

from .models import LigneService, Reservation, Service

admin.site.register([Reservation, Service, LigneService])

from django.contrib import admin

from .models import Event, Reservation, Seat

admin.site.register(Event)
admin.site.register(Reservation)
admin.site.register(Seat)

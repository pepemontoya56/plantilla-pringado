from django.contrib import admin

# Register your models here.
from .models import ProfileUser, Partida

admin.sites.register(Partida)
admin.sites.register(ProfileUser)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class HotelUserAdmin(UserAdmin):
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Infos', {'fields': ('first_name', 'last_name', 'phone', 'role')}),
        ('Droits', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'role', 'password1', 'password2')}),)
    search_fields = ('email',)

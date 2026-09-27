from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("HelpDesk", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff", "is_active")

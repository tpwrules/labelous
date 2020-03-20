from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    ordering = ('email',)
    exclude = ('username',)

    # stolen from UserAdmin
    fieldsets = (
        (None, {'fields': ('password',)}),
        (('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups',
                'user_permissions'),
        }),
        (('Important dates'), {'fields': ('last_login', 'date_joined')}))

admin.site.register(User, CustomUserAdmin)

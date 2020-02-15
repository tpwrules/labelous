from django.contrib import admin

from .models import Image
class ImageAdmin(admin.ModelAdmin):
    readonly_fields = ('upload_time',)

admin.site.register(Image, ImageAdmin)

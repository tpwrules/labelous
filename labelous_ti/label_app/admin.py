from django.contrib import admin

from .models import Annotation
class AnnotationAdmin(admin.ModelAdmin):
    readonly_fields = ('creation_time', 'last_edit_time',)
admin.site.register(Annotation, AnnotationAdmin)

from .models import Polygon
class PolygonAdmin(admin.ModelAdmin):
    readonly_fields = ('creation_time', 'last_edit_time',)
admin.site.register(Polygon, PolygonAdmin)

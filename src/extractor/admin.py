from django.contrib import admin

from .models import ExtractionFilter, ExtractionLog

admin.site.register(ExtractionFilter)
admin.site.register(ExtractionLog)

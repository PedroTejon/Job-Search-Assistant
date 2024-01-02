from django.contrib import admin

from .models import Company, Listing

admin.site.register(Listing)
admin.site.register(Company)

from django.contrib import admin

from .models import Company, Listing

# user: admin, pass: admin


class ListingAdmin(admin.ModelAdmin):
    search_fields = ('title', 'platform_id')


class CompanyAdmin(admin.ModelAdmin):
    search_fields = ('id',)


admin.site.register(Listing, ListingAdmin)
admin.site.register(Company, CompanyAdmin)

from django.contrib import admin

from .models import RefreshToken


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "family", "created_at", "expires_at", "revoked_at", "ip_address")
    list_filter = ("revoked_at",)
    search_fields = ("user__username", "ip_address")
    readonly_fields = [f.name for f in RefreshToken._meta.fields]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

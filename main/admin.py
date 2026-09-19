from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from config.jinja import price
from .models import Booking, Destination, DestinationPhoto
from .thumbs import thumb_url


class DestinationPhotoInline(admin.TabularInline):
    model = DestinationPhoto
    extra = 1


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("preview", "display_name", "price_display", "photo_count", "is_published")
    list_display_links = ("preview", "display_name")
    list_editable = ("is_published",)
    list_filter = ("is_published",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at",)
    inlines = [DestinationPhotoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_photos=Count("photos"))

    @admin.display(description="Rasm")
    def preview(self, obj):
        return format_html('<img src="{}" width="72" height="48" style="object-fit:cover;border-radius:6px">', thumb_url(obj.image, 480))

    @admin.display(description="Narxi", ordering="price")
    def price_display(self, obj):
        return price(obj.price)

    @admin.display(description="Rasmlar", ordering="_photos")
    def photo_count(self, obj):
        return obj._photos


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "full_name", "phone", "destination", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "destination")
    list_select_related = ("destination",)
    search_fields = ("reference", "first_name", "last_name", "phone")
    readonly_fields = ("reference", "user", "created_at")
    date_hierarchy = "created_at"
    actions = ["confirm", "cancel"]

    @admin.action(description="Tanlangan bronlarni tasdiqlash")
    def confirm(self, request, queryset):
        queryset.update(status=Booking.Status.CONFIRMED)

    @admin.action(description="Tanlangan bronlarni bekor qilish")
    def cancel(self, request, queryset):
        queryset.update(status=Booking.Status.CANCELLED)

from django.contrib import admin
from django.utils.html import format_html
from .models import Blog, BlogImage


class BlogImageInline(admin.TabularInline):
    model = BlogImage
    extra = 3
    fields = ("image_preview", "image", "image_name")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="70" style="object-fit:cover;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Preview"


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "uploaded_by", "created_at", "image_count")
    search_fields = ("title", "uploaded_by")
    list_filter = ("created_at",)
    ordering = ("-created_at",)

    inlines = [BlogImageInline]

    fieldsets = (
        ("Blog Info", {
            "fields": ("title", "content")
        }),
        ("Author Info", {
            "fields": ("uploaded_by", "uploaded_by_image")
        }),
    )

    def image_count(self, obj):
        return obj.images.count()

    image_count.short_description = "Total Images"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("images")


@admin.register(BlogImage)
class BlogImageAdmin(admin.ModelAdmin):
    list_display = ("id", "blog", "image_name", "created_at")
    search_fields = ("image_name", "blog__title")
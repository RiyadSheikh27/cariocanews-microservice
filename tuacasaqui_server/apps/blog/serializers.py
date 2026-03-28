from rest_framework import serializers
from .models import Blog, BlogImage


class BlogImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = BlogImage
        fields = ["id", "image", "image_name"]

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class BlogSerializer(serializers.ModelSerializer):
    images = BlogImageSerializer(many=True, read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id",
            "title",
            "content",
            "uploaded_by",
            "uploaded_by_image",
            "images",
            "created_at",
            "updated_at",
        ]
    

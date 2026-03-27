from django.db import models
from apps.core.models import TimeStampedModel

# --- Model for Blog Post ---

class Blog(TimeStampedModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    uploaded_by = models.CharField(max_length=100)
    uploaded_by_image = models.FileField(upload_to='user_images/', null=True, blank=True)

    def __str__(self):
        return self.title
    
class BlogImage(TimeStampedModel):
    blog = models.ForeignKey(Blog, related_name='images', on_delete=models.CASCADE)
    image = models.FileField(upload_to='blog_images/', null=True, blank=True)
    image_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.blog.title}"
    

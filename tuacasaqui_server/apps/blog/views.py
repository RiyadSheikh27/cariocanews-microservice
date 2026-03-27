from rest_framework.views import APIView
from rest_framework import status
from django.db.models import Prefetch, Q

from .models import Blog, BlogImage
from .serializers import BlogSerializer
from apps.core.api_response import APIResponse
from apps.core.pagination import CustomPagination


class BlogListAPIView(APIView):
    def get(self, request):
        try:
            queryset = Blog.objects.all().prefetch_related(
                Prefetch(
                    "images",
                    queryset=BlogImage.objects.only(
                        "id", "image", "image_name", "blog_id"
                    ),
                )
            ).all()

        
            # 🔹 Search filter
            search = request.GET.get("search")
            uploaded_by = request.GET.get("uploaded_by")

            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) | Q(content__icontains=search)
                )

            if uploaded_by:
                queryset = queryset.filter(uploaded_by__icontains=uploaded_by)

            # Pagination
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)

            serializer = BlogSerializer(paginated_queryset, many=True)

            # Meta info
            meta = {
                "page": paginator.page.number,
                "page_size": paginator.get_page_size(request),
                "total_pages": paginator.page.paginator.num_pages,
                "total_items": paginator.page.paginator.count,
            }

            return APIResponse.success_response(
                data=serializer.data,
                message="Blogs fetched successfully",
                meta=meta,
                status_code=status.HTTP_200_OK,
            )

        except Exception as e:
            return APIResponse.error_response(
                errors=str(e),
                message="Failed to fetch blogs",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
class BlogDetailAPIView(APIView):
    def get(self, request, pk):
        try:
            blog = Blog.objects.prefetch_related(
                Prefetch(
                    "images",
                    queryset=BlogImage.objects.only("id", "image", "image_name", "blog_id")
                )
            ).all().get(pk=pk)

            serializer = BlogSerializer(blog)

            return APIResponse.success_response(
                data=serializer.data,
                message="Blog fetched successfully",
            )

        except Blog.DoesNotExist:
            return APIResponse.error_response(
                message="Blog not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return APIResponse.error_response(
                errors=str(e),
                message="Failed to fetch blog",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
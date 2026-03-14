from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone


class APIResponse:
    @staticmethod
    def success_response(
        data=None,
        message="Request Successful",
        status_code=status.HTTP_200_OK,
        meta=None,
    ):
        if meta is None:
            meta = {}
        meta["timestamp"] = timezone.now()

        return Response(
            {
                "success": True,
                "message": message,
                "data": data,
                "errors": None,
                "meta": meta,
            },
            status=status_code,
        )

    @staticmethod
    def error_response(
        errors=None,
        message="Something went wrong",
        status_code=status.HTTP_400_BAD_REQUEST,
        meta=None,
    ):
        if meta is None:
            meta = {}
        meta["timestamp"] = timezone.now()

        return Response(
            {
                "success": False,
                "message": message,
                "data": None,
                "errors": errors,
                "meta": meta,
            },
            status=status_code,
        )
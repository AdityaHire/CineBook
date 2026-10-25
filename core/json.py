from django.http import JsonResponse


def json_response(data, status=200):
    return JsonResponse(data, status=status)


def json_error(code, message, status, details=None):
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JsonResponse({"error": error}, status=status)

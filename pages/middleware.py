from django.http import HttpResponseForbidden
from .models import PageVisit


BLOCKED_USER_AGENT_KEYWORDS = [
    "axios",
    "python-requests",
    "curl",
    "wget",
    "scrapy",
    "bot",
    "spider",
    "crawler",
    "nikto",
    "sqlmap",
    "nmap",
    "masscan",
    "go-http-client",
]


BLOCKED_PATHS = [
    "/wp-admin",
    "/wp-login",
    "/cart",
    "/pricing",
    "/order",
    "/register",
    "/blog",
    "/contact",
]


# مسارات لا تسجّل كزيارة صفحة حقيقية (ملفات ثابتة، أيقونات، إلخ)
IGNORED_PATH_PREFIXES = [
    "/static/",
    "/media/",
    "/favicon.ico",
    "/apple-touch-icon",
    "/robots.txt",
]


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class BlockScannersMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        # ===== حظر بناءً على الـ User-Agent =====
        if any(keyword in user_agent for keyword in BLOCKED_USER_AGENT_KEYWORDS):
            return HttpResponseForbidden("Forbidden")

        # ===== حظر بناءً على المسار =====
        path = request.path.lower()

        if any(path.startswith(blocked) for blocked in BLOCKED_PATHS):
            return HttpResponseForbidden("Forbidden")

        response = self.get_response(request)

        # ===== تسجيل الزيارة الحقيقية (بعد ما مرت من كل الفلاتر فوق) =====
        try:
            if (
                request.method == "GET"
                and not any(path.startswith(p) for p in IGNORED_PATH_PREFIXES)
            ):
                PageVisit.objects.create(
                    path=request.path[:500],
                    method=request.method,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                    status_code=response.status_code,
                )
        except Exception:
            pass  # لا نوقف الموقع أبداً بسبب خطأ بتسجيل الإحصائيات

        return response
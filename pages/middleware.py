
from django.http import HttpResponseForbidden
from .models import PageVisit


# ==========================================
# عناوين IP المحظورة
# ==========================================
BLOCKED_IPS = [
    # أضف عنوان IP الحقيقي هنا بعد التأكد منه
    # مثال: "203.0.113.25",
]


# ==========================================
# كلمات مفتاحية لحظر البوتات والأدوات المزعجة
# ==========================================
BLOCKED_USER_AGENT_KEYWORDS = [
    "axios",
    "python-requests",
    "curl",
    "wget",
    "scrapy",
    "spider",
    "crawler",
    "nikto",
    "sqlmap",
    "nmap",
    "masscan",
    "go-http-client",
    "shapbot",
    "amazonbot",
    "semrushbot",
    "backlinksextendedbot",
    "applebot",
]


# ==========================================
# بوتات محركات البحث المسموح بها
# ==========================================
ALLOWED_BOTS = [
    "googlebot",
    "bingbot",
    "duckduckbot",
    "yandexbot",
    "baiduspider",
    "facebookexternalhit",
    "twitterbot",
    "slurp",
]


# ==========================================
# مسارات مشبوهة يتم حظرها
# ==========================================
BLOCKED_PATHS = [
    "/wp-admin",
    "/wp-login",
    "/wp-includes",
    "/wp-content",
    "/wp-json",
    "/xmlrpc.php",
    "/wlwmanifest.xml",
    "/cart",
    "/pricing",
    "/order",
    "/register",
    "/blog",
    "/contact",
]


# ==========================================
# مسارات لا تسجل كزيارات صفحات
# ==========================================
IGNORED_PATH_PREFIXES = [
    "/static/",
    "/media/",
    "/favicon.ico",
    "/apple-touch-icon",
    "/robots.txt",
    "/sitemap.xml",
    "/admin/",
]


# ==========================================
# استخراج عنوان IP
# ==========================================
def get_client_ip(request):
    x_forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR", ""
    )

    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "")


# ==========================================
# Middleware
# ==========================================
class BlockScannersMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # عنوان IP للطلب
        client_ip = get_client_ip(request)

        # حظر عناوين IP المحددة
        if client_ip in BLOCKED_IPS:
            return HttpResponseForbidden("Forbidden")

        # معلومات المتصفح
        user_agent = request.META.get(
            "HTTP_USER_AGENT", ""
        ).lower()

        # السماح لبوتات محركات البحث المعروفة
        if any(
            allowed in user_agent
            for allowed in ALLOWED_BOTS
        ):
            return self.get_response(request)

        # حظر الأدوات الآلية المزعجة
        if any(
            keyword in user_agent
            for keyword in BLOCKED_USER_AGENT_KEYWORDS
        ):
            return HttpResponseForbidden("Forbidden")

        # فحص المسارات المشبوهة
        path = request.path.lower()

        if any(
            blocked in path
            for blocked in BLOCKED_PATHS
        ):
            return HttpResponseForbidden("Forbidden")

        # معالجة الطلب بشكل طبيعي
        response = self.get_response(request)

        # تسجيل الزيارات مع المحافظة على النظام الحالي
        try:
            if (
                request.method == "GET"
                and not any(
                    path.startswith(prefix)
                    for prefix in IGNORED_PATH_PREFIXES
                )
            ):
                PageVisit.objects.create(
                    path=request.path[:500],
                    method=request.method,
                    ip_address=client_ip[:100],
                    user_agent=request.META.get(
                        "HTTP_USER_AGENT", ""
                    )[:500],
                    status_code=response.status_code,
                )

        except Exception:
            # لا نوقف الموقع بسبب خطأ في تسجيل الإحصائيات
            pass

        return response

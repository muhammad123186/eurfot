import uuid

from django.conf import settings
from django.http import HttpResponseForbidden
import ipaddress

from .models import PageVisit


# ==========================================
# عناوين IP المحظورة
# ==========================================
BLOCKED_IPS = [
    "47.79.200.147",
    "47.79.207.180",
    "47.79.206.106",
    "47.79.201.140",
]

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("47.79.201.0/24"),
    ipaddress.ip_network("47.79.206.0/24"),
    ipaddress.ip_network("47.79.207.0/24"),
    ipaddress.ip_network("47.79.200.0/24"),
]


# ==========================================
# كلمات مفتاحية لحظر الأدوات الآلية
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
# مسارات محظورة
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
# مسارات لا تسجل كمشاهدات صفحات
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
# إعدادات Cookie
# ==========================================
VISITOR_COOKIE_NAME = "eurfot_visitor_id"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2


# ==========================================
# استخراج عنوان IP
# ==========================================
def get_client_ip(request):
    remote_addr = request.META.get("REMOTE_ADDR", "")
    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR", ""
    )

    # أبقينا التسجيل التشخيصي الحالي
    print("REMOTE_ADDR:", remote_addr)
    print("X_FORWARDED_FOR:", forwarded_for)

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return remote_addr


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

        try:
            client_ip_obj = ipaddress.ip_address(client_ip)

            if any(
                client_ip_obj in network
                for network in BLOCKED_IP_NETWORKS
            ):
                print("BLOCKED IP NETWORK:", client_ip)
                return HttpResponseForbidden("Forbidden")

        except ValueError:
            pass

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

        # ======================================
        # قراءة معرّف المتصفح من Cookie
        # ======================================
        cookie_value = request.COOKIES.get(
            VISITOR_COOKIE_NAME
        )

        set_visitor_cookie = False

        try:
            if cookie_value:
                visitor_id = uuid.UUID(cookie_value)
            else:
                raise ValueError("Missing visitor cookie")

        except (ValueError, TypeError, AttributeError):
            visitor_id = uuid.uuid4()
            set_visitor_cookie = True

        # ======================================
        # معالجة الطلب
        # ======================================
        response = self.get_response(request)

        # ======================================
        # تسجيل الزيارات
        # ======================================
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
                    ip_address=client_ip or None,
                    user_agent=request.META.get(
                        "HTTP_USER_AGENT", ""
                    )[:500],
                    visitor_id=visitor_id,
                    status_code=response.status_code,
                )

        except Exception as e:
            print("PageVisit tracking error:", repr(e))

        # ======================================
        # إرسال Cookie إلى المتصفح
        # ======================================
        if set_visitor_cookie:
            response.set_cookie(
                key=VISITOR_COOKIE_NAME,
                value=str(visitor_id),
                max_age=VISITOR_COOKIE_MAX_AGE,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                path="/",
            )

        return response
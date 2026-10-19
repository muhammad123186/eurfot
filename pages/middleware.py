
import uuid
import ipaddress

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden

from .models import PageVisit


# ==========================================
# نطاقات IP محظورة بالكامل
# ==========================================
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("47.79.200.0/21"),
]


# ==========================================
# حدود طلبات صفحات اللاعبين
# ==========================================
IP_PLAYER_LIMIT = 3
IP_PLAYER_WINDOW = 60

PLAYER_REQUEST_LIMIT = 3
PLAYER_REQUEST_WINDOW_SECONDS = 60


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
# بوتات محركات البحث وأدوات فحص Google
# ==========================================
ALLOWED_BOTS = [
    "googlebot",
    "google-inspectiontool",
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
# مسارات لا تسجل كمشاهدات
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
    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")

    if cf_ip:
        return cf_ip.strip()

    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR", ""
    )

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "")


def is_ip_blocked(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False

    return any(
        addr in network
        for network in BLOCKED_IP_NETWORKS
    )


# ==========================================
# Middleware
# ==========================================
class BlockScannersMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = get_client_ip(request)
        path = request.path.lower()

        user_agent = request.META.get(
            "HTTP_USER_AGENT", ""
        ).lower()

        # ======================================
        # حظر نطاقات IP المعروفة
        # ======================================
        if is_ip_blocked(client_ip):
            return HttpResponseForbidden("Forbidden")

        # ======================================
        # تحديد البوتات المعروفة بالاسم
        # تنبيه: User-Agent وحده لا يثبت هوية البوت
        # ======================================
        is_allowed_bot = any(
            bot in user_agent
            for bot in ALLOWED_BOTS
        )

        # ======================================
        # حظر الأدوات الآلية المزعجة
        # ======================================
        if not is_allowed_bot and any(
            keyword in user_agent
            for keyword in BLOCKED_USER_AGENT_KEYWORDS
        ):
            return HttpResponseForbidden("Forbidden")

        # ======================================
        # فحص المسارات المحظورة
        # ======================================
        if any(
            blocked in path
            for blocked in BLOCKED_PATHS
        ):
            return HttpResponseForbidden("Forbidden")

        # ======================================
        # قراءة أو إنشاء معرّف الزائر
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
        # تحديد صفحات اللاعبين
        # ======================================
        is_player_page = (
            request.method == "GET"
            and path.startswith("/player/")
        )

        # ======================================
        # تحديد معدل الطلبات حسب IP
        # نستثني البوتات المدرجة في ALLOWED_BOTS
        # ======================================
        if (
            is_player_page
            and client_ip
            and not is_allowed_bot
        ):
            rate_key = f"player_rate_{client_ip}"
            count = cache.get(rate_key, 0)

            if count >= IP_PLAYER_LIMIT:
                response = HttpResponse(
                    "تم تجاوز الحد المسموح. يرجى الانتظار قليلًا.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )

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

            cache.set(
                rate_key,
                count + 1,
                IP_PLAYER_WINDOW,
            )

        # ======================================
        # معالجة الطلب أولًا
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
        # إرسال Cookie بعد إنشاء الاستجابة
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
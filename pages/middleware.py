from django.http import HttpResponseForbidden


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


class BlockScannersMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        # ===== حظر بناءً على الـ User-Agent =====
        if any(keyword in user_agent for keyword in BLOCKED_USER_AGENT_KEYWORDS):
            return HttpResponseForbidden("Forbidden")

        # ===== حظر بناءً على المسار (لو حدا وصلها بمتصفح حقيقي أصلاً) =====
        path = request.path.lower()

        if any(path.startswith(blocked) for blocked in BLOCKED_PATHS):
            return HttpResponseForbidden("Forbidden")

        response = self.get_response(request)
        return response
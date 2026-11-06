class BrowserSecurityHeadersMiddleware:
    """Apply a narrow browser policy without weakening Django's built-in protections."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(
                (
                    "default-src 'self'",
                    "base-uri 'self'",
                    "object-src 'none'",
                    "frame-ancestors 'none'",
                    "form-action 'self'",
                    "img-src 'self' data:",
                    "font-src 'self' https://fonts.gstatic.com",
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com",
                    "connect-src 'self'",
                )
            ),
        )
        response.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
        return response

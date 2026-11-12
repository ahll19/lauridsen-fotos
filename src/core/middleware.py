"""Middleware that repairs what sitting behind a reverse proxy breaks."""

from django.conf import settings


def real_client_ip(request):
    """
    The address of the visitor, rather than of the proxy in front of the application.

    nginx sets `X-Forwarded-For: $proxy_add_x_forwarded_for`, which is any header the
    client sent with the address nginx actually saw **appended**. So the trustworthy end
    of the list is the right-hand one: everything to the left of it was supplied by the
    caller and can say anything at all.

    TRUSTED_PROXY_COUNT is how many hops at that end belong to us — one for nginx alone,
    as on a laptop, and two on the server, where the TLS-terminating proxy is in front.
    Counting in from the right by exactly that many is what makes the result unspoofable:
    a forged entry can only ever land further left than the hops we control.
    """
    remote_addr = request.META.get("REMOTE_ADDR")
    trusted = settings.TRUSTED_PROXY_COUNT
    if trusted <= 0:
        return remote_addr

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    if not chain:
        return remote_addr

    # Never count past the start of the chain, or a short header would hand back the
    # left-most (client-supplied) entry — precisely the value being defended against.
    return chain[-min(trusted, len(chain))]


class ClientIPMiddleware:
    """
    Put the visitor's own address into REMOTE_ADDR.

    Behind nginx every request reaches the application from the proxy's container
    address, so REMOTE_ADDR is identical for every visitor on earth. Anything keyed on it
    therefore shares one bucket: the contact form's rate limit, applied per IP, was in
    practice a single global limit that one sender could exhaust for everybody.

    Django has no setting for this, and the fix has to happen before any view reads the
    value, so it is done here. The proxy's own address is kept under a separate key for
    debugging rather than discarded.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.META["PROXY_REMOTE_ADDR"] = request.META.get("REMOTE_ADDR")
        request.META["REMOTE_ADDR"] = real_client_ip(request)
        return self.get_response(request)


class ContentSecurityPolicyMiddleware:
    """
    Send a Content-Security-Policy with every response the application renders.

    The other security headers stop the page being framed or mis-sniffed; this is the one
    that contains a script someone managed to inject, by telling the browser that nothing
    is allowed to run or load unless it came from this site. It became straightforward to
    write once the fonts stopped coming from a third party — the policy has no external
    host in it at all.

    The policy itself is a setting (DJANGO_CSP), so it can be loosened for a new embed or
    switched to report-only without a code change. A response that already carries the
    header keeps its own.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.policy = settings.CONTENT_SECURITY_POLICY
        self.header = (
            "Content-Security-Policy-Report-Only"
            if settings.CONTENT_SECURITY_POLICY_REPORT_ONLY
            else "Content-Security-Policy"
        )

    def __call__(self, request):
        response = self.get_response(request)
        if self.policy and self.header not in response:
            response[self.header] = self.policy
        return response

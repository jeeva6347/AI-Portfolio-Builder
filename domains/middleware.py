"""
Module 13: Custom Domains — middleware.py

CustomDomainMiddleware intercepts incoming HTTP requests on registered custom domains
and serves the compiled portfolio preview directly at the root path.
"""
import os
import logging
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.utils.deprecation import MiddlewareMixin
from django.db.models import Q

from domains.models import CustomDomain
from portfolio.models import Portfolio
from themes.services import apply_theme_mapping
from analytics.services.tracking_service import track_visit
from analytics.services.seo_service import inject_seo_metadata

logger = logging.getLogger(__name__)


class CustomDomainMiddleware(MiddlewareMixin):
    """
    Middleware to resolve custom domains mapped to portfolios.
    If request is on a registered and active custom domain, serves the portfolio.
    """

    def process_request(self, request):
        host = request.get_host().split(":")[0].lower()

        # Skip platform / local development hosts
        platform_domains = getattr(settings, "PLATFORM_DOMAINS", ["localhost", "127.0.0.1", "testserver"])
        if host in platform_domains:
            return None

        # Check all possible subdomain / domain divisions
        parts = host.split(".")
        matches = []
        for i in range(1, len(parts)):
            subdomain = ".".join(parts[:i])
            domain_name = ".".join(parts[i:])
            matches.append((subdomain, domain_name))
        matches.append(("", host))

        query = Q()
        for sub, dom in matches:
            query |= Q(subdomain=sub, domain_name=dom)

        custom_domain = (
            CustomDomain.objects.filter(query, status=CustomDomain.Status.ACTIVE)
            .select_related("portfolio", "portfolio__selected_theme")
            .first()
        )

        if not custom_domain:
            return None

        # Serve the mapped portfolio. Limit non-root paths unless they are sitemap/robots
        path = request.path
        if path != "/":
            if path in ["/sitemap.xml", "/robots.txt"]:
                return None
            raise Http404("Page not found on this custom domain.")

        portfolio = custom_domain.portfolio

        # Security check: Private draft check
        if portfolio.status != Portfolio.Status.PUBLISHED and portfolio.user != request.user:
            return HttpResponseForbidden("This portfolio draft is unpublished and private.")

        theme = portfolio.selected_theme
        if not theme:
            return HttpResponse(
                "<h3>No active theme selected.</h3><p>Please select a theme to render your portfolio.</p>",
                content_type="text/html"
            )

        # Premium theme subscription validation check
        if theme.is_premium:
            from payments.permissions import get_user_plan_benefits
            plan = get_user_plan_benefits(portfolio.user)
            if not plan.premium_themes_enabled:
                return HttpResponse(
                    "<h3>Premium Theme Required</h3><p>This portfolio template requires a Premium subscription upgrade.</p>",
                    content_type="text/html",
                    status=403
                )

        mapping = theme.mappings.filter(is_active=True).first()
        if not mapping:
            return HttpResponse(
                f"<h3>Theme '{theme.name}' does not have an active mapping profile.</h3>",
                content_type="text/html"
            )

        index_path = theme.index_html_path
        if not index_path or not os.path.exists(index_path):
            return HttpResponse("Theme files are missing or incomplete.", status=404)

        with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        compiled_html = apply_theme_mapping(html_content, mapping, portfolio.get_fields_dict())

        # Log traffic metrics
        try:
            track_visit(request, portfolio)
        except Exception as exc:
            logger.warning("Failed to track custom domain visit: %s", exc)

        # Inject SEO metadata
        compiled_html = inject_seo_metadata(compiled_html, portfolio, request=request)

        return HttpResponse(compiled_html, content_type="text/html")

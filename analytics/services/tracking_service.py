from urllib.parse import urlparse
from django.utils import timezone
from ..models import PortfolioVisit, PortfolioMetric


def track_visit(request, portfolio):
    """
    Records a visit metric event to the database.
    Excludes the portfolio owner to prevent inflating user metrics.
    """
    # 1. Access checks: Exclude owner visits
    if request.user.is_authenticated and request.user == portfolio.user:
        return None

    # 2. Extract visitor metadata from User Agent
    ua = request.META.get("HTTP_USER_AGENT", "")
    device_type = "Desktop"
    if "Mobi" in ua or "Android" in ua:
        device_type = "Mobile"
    elif "iPad" in ua or "Tablet" in ua:
        device_type = "Tablet"

    # Identify browser details
    browser = "Other"
    ua_lower = ua.lower()
    if "chrome" in ua_lower and "edge" not in ua_lower and "edg" not in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "Safari"
    elif "edge" in ua_lower or "edg" in ua_lower:
        browser = "Edge"
    elif "opera" in ua_lower or "opr" in ua_lower:
        browser = "Opera"

    # 3. Referrer parsing
    referrer_url = request.META.get("HTTP_REFERER", "")
    if referrer_url:
        parsed_ref = urlparse(referrer_url)
        referrer = parsed_ref.netloc or "direct"
    else:
        referrer = "direct"

    # 4. IP and Geography (Mock IP extraction and CF country fallback check)
    ip_address = request.META.get("HTTP_X_FORWARDED_FOR")
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()
    else:
        ip_address = request.META.get("REMOTE_ADDR")

    country = request.META.get("HTTP_CF_IPCOUNTRY", "United States")
    if country == "Unknown" or not country:
        country = "United States"

    # 5. Path page indicator (e.g. Home, projects, contact mapped from page query arg)
    path = request.GET.get("page", "Home")
    if not path:
        path = "Home"

    # 6. Session tracking for unique/returning check
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Record specific transaction visit log
    visit = PortfolioVisit.objects.create(
        portfolio=portfolio,
        session_id=session_key,
        ip_address=ip_address,
        device_type=device_type,
        browser=browser,
        referrer=referrer,
        country=country,
        path=path
    )

    # 7. Update PortfolioMetric summary counts
    metric, _ = PortfolioMetric.objects.get_or_create(portfolio=portfolio)
    
    # Calculate unique visitors
    all_visits = portfolio.visits.all()
    unique_visitors_count = all_visits.values("session_id").distinct().count()
    total_visits_count = all_visits.count()
    
    # Returning visitors are sessions with more than 1 visit
    session_counts = {}
    for v in all_visits:
        session_counts[v.session_id] = session_counts.get(v.session_id, 0) + 1
    returning_visitors_count = sum(1 for count in session_counts.values() if count > 1)

    metric.total_visits = total_visits_count
    metric.unique_visitors = unique_visitors_count
    metric.returning_visitors = returning_visitors_count
    metric.save(update_fields=["total_visits", "unique_visitors", "returning_visitors"])

    return visit

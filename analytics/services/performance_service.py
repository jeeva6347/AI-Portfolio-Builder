from themes.models import ThemeAsset


def analyze_performance(portfolio):
    """
    Analyzes asset files of the portfolio's active theme and dynamically
    computes sizes, counts, performance score, and suggestions.
    """
    theme = portfolio.selected_theme
    
    # Defaults in case of no active theme selection
    results = {
        "portfolio_size": 0,
        "assets_count": 0,
        "image_count": 0,
        "css_size": 0,
        "js_size": 0,
        "html_size": 0,
        "image_size": 0,
        "other_size": 0,
        "largest_assets": [],
        "performance_score": 100,
        "suggestions": []
    }

    if not theme:
        results["suggestions"].append("Please select a Theme layout to analyze speed metrics.")
        results["performance_score"] = 0
        return results

    # Retrieve all assets for this theme
    assets = theme.assets.all()
    results["assets_count"] = assets.count()

    # Aggregate file sizes by category
    for asset in assets:
        size = asset.file_size or 0
        atype = asset.asset_type
        
        results["portfolio_size"] += size
        
        if atype == ThemeAsset.AssetType.CSS:
            results["css_size"] += size
        elif atype == ThemeAsset.AssetType.JS:
            results["js_size"] += size
        elif atype == ThemeAsset.AssetType.HTML:
            results["html_size"] += size
        elif atype == ThemeAsset.AssetType.IMAGE:
            results["image_size"] += size
            results["image_count"] += 1
        else:
            results["other_size"] += size

    # Retrieve top 5 largest assets
    largest = assets.order_by("-file_size")[:5]
    for asset in largest:
        results["largest_assets"].append({
            "name": asset.file_path,
            "size": asset.file_size,
            "type": asset.get_asset_type_display()
        })

    # Speed Score & Recommendation Penalties
    score = 100
    suggestions = []

    # 1. Total size threshold (Max 1MB recommended)
    total_mb = results["portfolio_size"] / (1024 * 1024)
    if total_mb > 2.0:
        score -= 25
        suggestions.append("Your portfolio page weight exceeds 2MB. Consider compressing heavy graphics assets.")
    elif total_mb > 1.0:
        score -= 15
        suggestions.append("Page weight is above 1MB. Optimize images to decrease load times.")

    # 2. CSS size recommendation (Max 100KB)
    css_kb = results["css_size"] / 1024
    if css_kb > 150:
        score -= 15
        suggestions.append("Large CSS files detected (>150KB). Minify stylesheet files and remove unused classes.")

    # 3. JavaScript size recommendation (Max 250KB)
    js_kb = results["js_size"] / 1024
    if js_kb > 300:
        score -= 15
        suggestions.append("Heavy JavaScript bundles (>300KB). Minify JS elements and defer non-critical script tags.")

    # 4. Images count suggestion
    if results["image_count"] > 10:
        suggestions.append("High number of image files (>10). Implement native lazy loading (loading='lazy') for images.")

    # 5. Favicon check
    has_favicon = False
    if hasattr(portfolio, "seo") and portfolio.seo.favicon:
        has_favicon = True
        
    if not has_favicon:
        score -= 10
        suggestions.append("Browser favicon is missing. Upload a favicon in the SEO tab to improve UX.")

    # Bound score
    results["performance_score"] = max(0, min(score, 100))
    results["suggestions"] = suggestions

    # Save to metrics table
    if hasattr(portfolio, "metric"):
        portfolio.metric.performance_score = results["performance_score"]
        portfolio.metric.save(update_fields=["performance_score"])

    return results

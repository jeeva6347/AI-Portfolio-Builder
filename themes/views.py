import os
import shutil
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings

from .models import Theme, ThemeCategory, ThemeAsset
from .forms import ThemeUploadForm
from .services import process_theme_upload, ThemeUploadError


def _base_context(request):
    return {
        "active_tab": "themes",
    }


class ThemeGalleryView(LoginRequiredMixin, View):
    """
    My Themes Gallery view.
    Displays uploaded themes, preview option, edit, delete, and publish buttons.
    """
    template_name = "themes/gallery.html"

    def get(self, request):
        themes = Theme.objects.filter(is_active=True).order_by("-created_at")
        user_themes = themes.filter(uploaded_by=request.user)
        system_themes = themes.filter(uploaded_by__isnull=True)

        ctx = _base_context(request)
        ctx.update({
            "themes": themes,
            "user_themes": user_themes,
            "system_themes": system_themes,
            "total_count": themes.count(),
        })
        return render(request, self.template_name, ctx)


class ThemeUploadView(LoginRequiredMixin, View):
    """
    Theme Upload is managed exclusively via the Admin interface.
    """
    def get(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return redirect("/admin/themes/theme/add/")
        messages.info(request, "Theme upload is managed by system administrators via the Admin Panel.")
        return redirect("themes:gallery")

    def post(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return redirect("/admin/themes/theme/add/")
        messages.info(request, "Theme upload is managed by system administrators via the Admin Panel.")
        return redirect("themes:gallery")


class ThemeEditView(LoginRequiredMixin, View):
    """
    Edit Theme details (Name, Description, Thumbnail/Preview Image).
    """
    template_name = "themes/edit.html"

    def get(self, request, pk):
        theme = get_object_or_404(Theme, pk=pk)
        if theme.uploaded_by and theme.uploaded_by != request.user and not request.user.is_staff:
            messages.error(request, "Permission denied.")
            return redirect("themes:gallery")

        ctx = _base_context(request)
        ctx["theme"] = theme
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        theme = get_object_or_404(Theme, pk=pk)
        if theme.uploaded_by and theme.uploaded_by != request.user and not request.user.is_staff:
            messages.error(request, "Permission denied.")
            return redirect("themes:gallery")

        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        preview_image = request.FILES.get("preview_image")

        if name:
            theme.name = name
        if description:
            theme.description = description
        if preview_image:
            theme.thumbnail = preview_image

        theme.save()
        messages.success(request, f"Theme '{theme.name}' updated successfully.")
        return redirect("themes:gallery")


class ThemeDeleteView(LoginRequiredMixin, View):
    """
    Deletes a theme and removes its extracted directory from disk.
    """
    def post(self, request, pk):
        theme = get_object_or_404(Theme, pk=pk)
        if theme.uploaded_by and theme.uploaded_by != request.user and not request.user.is_staff:
            messages.error(request, "Permission denied.")
            return redirect("themes:gallery")

        theme_name = theme.name
        # Remove extracted directory
        if theme.extracted_path:
            dest_dir = os.path.join(settings.MEDIA_ROOT, theme.extracted_path)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir, ignore_errors=True)

        theme.delete()
        messages.success(request, f"Theme '{theme_name}' has been deleted.")
        return redirect("themes:gallery")


class ThemePreviewView(View):
    """
    Serves the live interactive preview of an extracted theme's index.html.
    Injects base tag so relative CSS/JS paths resolve properly from media root.
    """
    def get(self, request, pk):
        theme = get_object_or_404(Theme, pk=pk)
        if not theme.extracted_path:
            raise Http404("Theme extracted files not found.")

        index_path = theme.index_html_path
        if not index_path or not os.path.exists(index_path):
            raise Http404("Theme index.html not found.")

        with open(index_path, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()

        # Inject base href tag if not present
        if theme.index_html_url and "<base " not in html_content:
            base_href = theme.index_html_url.rsplit("index.html", 1)[0]
            base_tag = f'<base href="{base_href}">'
            if "<head>" in html_content:
                html_content = html_content.replace("<head>", f"<head>\n    {base_tag}", 1)

        return HttpResponse(html_content, content_type="text/html")

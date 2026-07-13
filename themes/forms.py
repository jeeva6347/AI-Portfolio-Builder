from django import forms
from .models import Theme, ThemeCategory, ThemeMapping
from .services import MAX_ZIP_SIZE_BYTES


class ThemeUploadForm(forms.ModelForm):
    """
    Form for Admin/Super Admin to upload a new theme.
    Includes the zip file field + basic metadata.
    """
    zip_file = forms.FileField(
        label="Theme ZIP File",
        help_text=f"Upload a .zip file containing index.html and assets. Max size: {MAX_ZIP_SIZE_BYTES // 1024 // 1024} MB.",
        widget=forms.FileInput(attrs={"accept": ".zip", "id": "id_zip_file"}),
    )

    class Meta:
        model = Theme
        fields = ("name", "description", "category", "is_premium", "price", "tags", "version")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "tags": forms.TextInput(attrs={"placeholder": "minimal, dark, portfolio"}),
        }
        help_texts = {
            "tags": "Comma-separated tags to help users discover this theme.",
            "price": "Set to 0 for a free theme.",
        }

    def clean_zip_file(self):
        f = self.cleaned_data.get("zip_file")
        if f:
            if not f.name.lower().endswith(".zip"):
                raise forms.ValidationError("Only .zip files are accepted.")
            if f.size > MAX_ZIP_SIZE_BYTES:
                raise forms.ValidationError(
                    f"File too large ({f.size / 1024 / 1024:.1f} MB). Maximum is {MAX_ZIP_SIZE_BYTES // 1024 // 1024} MB."
                )
        return f

    def clean(self):
        cleaned = super().clean()
        is_premium = cleaned.get("is_premium")
        price = cleaned.get("price")
        if is_premium and (price is None or price <= 0):
            self.add_error("price", "Premium themes must have a price greater than $0.00.")
        if not is_premium and price and price > 0:
            # Auto-correct: if marked free but has a price, reset price to 0
            cleaned["price"] = 0
        return cleaned


class CategoryForm(forms.ModelForm):
    """Form for managing theme categories."""

    class Meta:
        model = ThemeCategory
        fields = ("name", "description", "icon")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "icon": forms.TextInput(attrs={"placeholder": "bi-grid-fill"}),
        }
        help_texts = {
            "icon": "Bootstrap Icons class name, e.g. 'bi-briefcase-fill'.",
        }


class ThemeRejectForm(forms.Form):
    """Simple form for providing a rejection reason."""
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Rejection Reason",
        help_text="This will be visible to the theme uploader.",
    )


class MarketplaceFilterForm(forms.Form):
    """GET-based filter form for the Marketplace page."""
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Search themes..."}),
    )
    category = forms.ModelChoiceField(
        queryset=ThemeCategory.objects.all(),
        required=False,
        empty_label="All Categories",
    )
    pricing = forms.ChoiceField(
        choices=[("", "Any"), ("free", "Free"), ("premium", "Premium")],
        required=False,
        label="Pricing",
    )
    sort = forms.ChoiceField(
        choices=[
            ("-created_at", "Latest"),
            ("-downloads", "Most Downloaded"),
            ("name", "Name A-Z"),
            ("price", "Price Low-High"),
        ],
        required=False,
        initial="-created_at",
        label="Sort By",
    )


class ThemeMappingForm(forms.ModelForm):
    """
    Form to create or update ThemeMapping profile metadata.
    """
    class Meta:
        model = ThemeMapping
        fields = ("name", "notes", "is_active")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "is_active": "If active, other profiles for this theme will be deactivated.",
        }


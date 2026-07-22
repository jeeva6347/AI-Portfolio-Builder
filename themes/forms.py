from django import forms
from .models import Theme, ThemeCategory
from .services import MAX_ZIP_SIZE_BYTES


class ThemeUploadForm(forms.ModelForm):
    """
    Form for users or admins to upload a new theme ZIP.
    Supports HTML5, CSS3, JS, Bootstrap 5, Tailwind CSS themes.
    """
    zip_file = forms.FileField(
        label="Theme ZIP Archive (theme.zip)",
        help_text=f"Upload a .zip file containing index.html, manifest.json, and assets. Max size: {MAX_ZIP_SIZE_BYTES // 1024 // 1024} MB.",
        widget=forms.FileInput(attrs={"accept": ".zip", "class": "form-control", "id": "id_zip_file"}),
    )

    class Meta:
        model = Theme
        fields = ("name", "description", "category", "tags", "version")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Modern Glass Portfolio"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Describe your theme layout, styles, and features..."}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "tags": forms.TextInput(attrs={"class": "form-control", "placeholder": "glassmorphism, dark, bootstrap, portfolio"}),
            "version": forms.TextInput(attrs={"class": "form-control", "placeholder": "1.0.0"}),
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

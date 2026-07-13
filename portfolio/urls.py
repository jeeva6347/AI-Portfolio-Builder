from django.urls import path
from . import views

app_name = "portfolio"

urlpatterns = [
    # Main Builder
    path("builder/", views.PortfolioBuilderView.as_view(), name="builder"),

    # Skill URLs
    path("skills/create/", views.SkillCreateView.as_view(), name="skill_create"),
    path("skills/<int:pk>/delete/", views.SkillDeleteView.as_view(), name="skill_delete"),

    # Project URLs
    path("projects/create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("projects/<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),

    # Experience URLs
    path("experience/create/", views.ExperienceCreateView.as_view(), name="experience_create"),
    path("experience/<int:pk>/delete/", views.ExperienceDeleteView.as_view(), name="experience_delete"),

    # Education URLs
    path("education/create/", views.EducationCreateView.as_view(), name="education_create"),
    path("education/<int:pk>/delete/", views.EducationDeleteView.as_view(), name="education_delete"),

    # Certificate URLs
    path("certificates/create/", views.CertificateCreateView.as_view(), name="certificate_create"),
    path("certificates/<int:pk>/delete/", views.CertificateDeleteView.as_view(), name="certificate_delete"),

    # Service URLs
    path("services/create/", views.ServiceCreateView.as_view(), name="service_create"),
    path("services/<int:pk>/delete/", views.ServiceDeleteView.as_view(), name="service_delete"),

    # Testimonial URLs
    path("testimonials/create/", views.TestimonialCreateView.as_view(), name="testimonial_create"),
    path("testimonials/<int:pk>/delete/", views.TestimonialDeleteView.as_view(), name="testimonial_delete"),

    # Theme & Preview URLs
    path("theme/", views.SelectThemeView.as_view(), name="select_theme"),
    path("preview/", views.UserPortfolioPreview.as_view(), name="preview"),
]

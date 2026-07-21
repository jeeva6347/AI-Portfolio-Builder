import uuid
from django.db import models
from django.conf import settings
from django.urls import reverse


class Portfolio(models.Model):
    """
    Main portfolio container representing a user's personal details,
    custom social links, contact form configs, and selected theme.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )
    
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Current publication status of the portfolio"
    )
    selected_theme = models.ForeignKey(
        "themes.Theme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolios",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolios",
    )
    
    # Personal Info
    name = models.CharField(max_length=150, blank=True)
    title = models.CharField(max_length=150, blank=True, help_text="e.g. Senior Backend Engineer")
    tagline = models.CharField(max_length=255, blank=True, help_text="A short tagline or catchphrase")
    about = models.TextField(blank=True, help_text="Rich about me biography description")
    photo = models.ImageField(upload_to="portfolios/photos/", null=True, blank=True)
    cover = models.ImageField(upload_to="portfolios/covers/", null=True, blank=True)
    
    # Direct Contact Info
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True, help_text="e.g. San Francisco, CA")
    resume = models.FileField(upload_to="portfolios/resumes/", null=True, blank=True)

    # Social Media URL Links
    social_github = models.URLField(blank=True)
    social_linkedin = models.URLField(blank=True)
    social_twitter = models.URLField(blank=True)
    social_instagram = models.URLField(blank=True)
    social_youtube = models.URLField(blank=True)
    social_facebook = models.URLField(blank=True)
    social_portfolio = models.URLField(blank=True)

    # Contact section custom display (optional overrides)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_address = models.CharField(max_length=255, blank=True)
    contact_form_action = models.URLField(blank=True, help_text="Custom POST link target for the contact form")

    # Footer
    footer_copyright = models.CharField(max_length=255, blank=True)
    footer_tagline = models.CharField(max_length=255, blank=True)

    # Publishing & Build Pipeline (Phase 7.1)
    class BuildStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        BUILDING = "BUILDING", "Building"
        PUBLISHED = "PUBLISHED", "Published"
        FAILED = "FAILED", "Failed"

    build_status = models.CharField(
        max_length=20,
        choices=BuildStatus.choices,
        default=BuildStatus.DRAFT,
        help_text="Current build state of the portfolio"
    )
    published_at = models.DateTimeField(null=True, blank=True)
    published_version = models.ForeignKey(
        "PortfolioVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_published_portfolios"
    )
    last_publish_error = models.TextField(blank=True)
    build_time_ms = models.PositiveIntegerField(default=0)
    html_size_bytes = models.PositiveIntegerField(default=0)
    css_size_bytes = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Portfolio"
        verbose_name_plural = "User Portfolios"

    def __str__(self):
        return f"{self.user.username}'s Portfolio"

    def get_fields_dict(self) -> dict:
        """
        Serializes all portfolio fields (including related lists)
        into a flat-key dict structure matching themes.fields.PORTFOLIO_FIELDS.
        """
        data = {
            # Personal
            "personal.name": self.name or self.user.get_full_name() or self.user.username,
            "personal.title": self.title,
            "personal.tagline": self.tagline,
            "personal.about": self.about,
            "personal.photo": self.photo.url if self.photo else "",
            "personal.cover": self.cover.url if self.cover else "",
            "personal.email": self.email or self.user.email,
            "personal.phone": self.phone,
            "personal.address": self.address,
            "personal.resume_url": self.resume.url if self.resume else "",
            
            # Socials
            "social.github": self.social_github,
            "social.linkedin": self.social_linkedin,
            "social.twitter": self.social_twitter,
            "social.instagram": self.social_instagram,
            "social.youtube": self.social_youtube,
            "social.facebook": self.social_facebook,
            "social.portfolio": self.social_portfolio,
            
            # Contact
            "contact.email": self.contact_email or self.email or self.user.email,
            "contact.phone": self.contact_phone or self.phone,
            "contact.address": self.contact_address or self.address,
            "contact.form_action": self.contact_form_action or "#",
            
            # Footer
            "footer.copyright": self.footer_copyright or f"© {self.name or self.user.username}. All rights reserved.",
            "footer.tagline": self.footer_tagline,
        }

        # Retrieve related lists
        # Skills (Optimized to filter in-memory, avoiding extra queries if prefetched)
        all_skills = list(self.skills.all())
        data["skills.technical"] = ", ".join([s.name for s in all_skills if s.skill_type == "technical"])
        data["skills.soft"] = ", ".join([s.name for s in all_skills if s.skill_type == "soft"])
        data["skills.languages"] = ", ".join([s.name for s in all_skills if s.skill_type == "language"])
        data["skills.frameworks"] = ", ".join([s.name for s in all_skills if s.skill_type == "framework"])
        data["skills.tools"] = ", ".join([s.name for s in all_skills if s.skill_type == "tool"])

        # Dynamic lists for visual repeating mapping structures
        data["projects.list"] = [
            {
                "projects.title": p.title,
                "projects.description": p.description,
                "projects.tech": p.technologies,
                "projects.github_url": p.github_url,
                "projects.live_url": p.live_url,
                "projects.image": p.image.url if p.image else "",
            }
            for p in self.projects.all()
        ]

        data["experience.list"] = [
            {
                "experience.company": e.company,
                "experience.position": e.position,
                "experience.duration": e.duration,
                "experience.description": e.description,
            }
            for e in self.experiences.all()
        ]

        data["education.list"] = [
            {
                "education.degree": ed.degree,
                "education.college": ed.college,
                "education.university": ed.university,
                "education.year": ed.year,
            }
            for ed in self.education.all()
        ]

        data["certificates.list"] = [
            {
                "certificates.name": c.name,
                "certificates.issuer": c.issuer,
                "certificates.year": c.year,
                "certificates.url": c.url,
            }
            for c in self.certificates.all()
        ]

        data["services.list"] = [
            {
                "services.title": s.title,
                "services.description": s.description,
                "services.icon": s.icon,
            }
            for s in self.services.all()
        ]

        data["testimonials.list"] = [
            {
                "testimonials.name": t.reviewer_name,
                "testimonials.role": t.reviewer_role,
                "testimonials.text": t.text,
            }
            for t in self.testimonials.all()
        ]

        return data


class PortfolioSkill(models.Model):
    """User skills classified into groups."""
    TYPE_CHOICES = [
        ("technical", "Technical Skill"),
        ("soft", "Soft Skill"),
        ("language", "Language"),
        ("framework", "Framework / Library"),
        ("tool", "Tool / DevOps"),
    ]
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="skills")
    skill_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="technical")
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=50, blank=True, help_text="e.g. Intermediate, Expert")

    class Meta:
        ordering = ["skill_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_skill_type_display()})"


class PortfolioProject(models.Model):
    """Showcased projects in user's portfolio."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    technologies = models.CharField(max_length=255, blank=True, help_text="Comma-separated stack, e.g. Python, Vue")
    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    image = models.ImageField(upload_to="portfolios/projects/", null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class PortfolioExperience(models.Model):
    """Work experience records."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField(max_length=150)
    position = models.CharField(max_length=150)
    duration = models.CharField(max_length=100, help_text="e.g. Jan 2020 - Present")
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.position} at {self.company}"


class PortfolioEducation(models.Model):
    """Education records."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="education")
    degree = models.CharField(max_length=150)
    college = models.CharField(max_length=150)
    university = models.CharField(max_length=150, blank=True)
    year = models.CharField(max_length=50, help_text="e.g. 2018 or 2015 - 2019")
    order = models.PositiveSmallIntegerField(default=0, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.degree} from {self.college}"


class PortfolioCertificate(models.Model):
    """Earned certifications."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="certificates")
    name = models.CharField(max_length=150)
    issuer = models.CharField(max_length=150)
    year = models.CharField(max_length=50)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class PortfolioService(models.Model):
    """Professional services offered."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="services")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, default="bi-gear-fill", help_text="Bootstrap Icons class name")

    def __str__(self):
        return self.title


class PortfolioTestimonial(models.Model):
    """Client recommendations."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="testimonials")
    reviewer_name = models.CharField(max_length=150)
    reviewer_role = models.CharField(max_length=150, blank=True, help_text="e.g. Product Lead, Google")
    text = models.TextField()

    def __str__(self):
        return f"Testimonial from {self.reviewer_name}"


class PortfolioVersion(models.Model):
    """
    Version history snapshot model for portfolios (Phase 6.1).
    Stores serialized portfolio states for draft editing, rollback, and comparison.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="versions"
    )
    version_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    snapshot_json = models.JSONField(default=dict)
    theme = models.ForeignKey(
        "themes.Theme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolio_versions"
    )
    seo_snapshot = models.JSONField(default=dict, blank=True)
    tag = models.CharField(max_length=50, default="Draft", help_text="e.g. Draft, Published, Rollback, Autosave")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_portfolio_versions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    is_auto_save = models.BooleanField(default=False)
    is_manual_save = models.BooleanField(default=False)
    git_commit_sha = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ["-version_number", "-created_at"]
        verbose_name = "Portfolio Version"
        verbose_name_plural = "Portfolio Versions"

    def __str__(self):
        return f"{self.portfolio.name} v{self.version_number} [{self.tag}]"


class PortfolioBuildLog(models.Model):
    """
    Log record for publishing pipeline execution steps (Phase 7.1).
    """
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="build_logs"
    )
    status = models.CharField(max_length=50)
    step = models.CharField(max_length=100)
    message = models.TextField()
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Portfolio Build Log"
        verbose_name_plural = "Portfolio Build Logs"

    def __str__(self):
        return f"[{self.step}] {self.status} - {self.portfolio.name}"


class PortfolioDeployment(models.Model):
    """
    Immutable deployment record for Phase 7.3 GitHub Deployment Engine.
    Tracks each deployment attempt, repository URLs, commit SHAs, and status.
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DEPLOYING = "DEPLOYING", "Deploying"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="portfolio_deployments"
    )
    provider = models.CharField(max_length=50, default="GITHUB")
    repository_name = models.CharField(max_length=255)
    repository_url = models.URLField(max_length=500, blank=True)
    branch = models.CharField(max_length=100, default="main")
    commit_sha = models.CharField(max_length=100, blank=True)
    deployment_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    deployment_url = models.URLField(max_length=500, blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_portfolio_deployments"
    )
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Portfolio Deployment"
        verbose_name_plural = "Portfolio Deployments"

    def __str__(self):
        return f"Deployment [{self.provider}] - {self.portfolio.name} ({self.deployment_status})"


class CoverLetter(models.Model):
    """
    CoverLetter model (Phase 9.2).
    Stores versioned AI-generated and user-edited cover letters linked to a portfolio draft.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="cover_letters")
    title = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True)
    company = models.CharField(max_length=255, blank=True)
    tone = models.CharField(max_length=50, default="Professional")
    length = models.CharField(max_length=50, default="Medium")
    template_variant = models.CharField(max_length=50, default="Modern")
    content_json = models.JSONField(default=dict, help_text="Stores greeting, introduction, body, closing, signature, evidence_map, coverage, metrics")
    content_text = models.TextField(blank=True, help_text="Full compiled plain text cover letter")
    version_number = models.PositiveIntegerField(default=1)
    content_hash = models.CharField(max_length=64, blank=True)
    job_hash = models.CharField(max_length=64, blank=True)
    resume_hash = models.CharField(max_length=64, blank=True)
    portfolio_hash = models.CharField(max_length=64, blank=True)
    metadata_json = models.JSONField(default=dict, help_text="Source, AI model, prompt version, generation time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version_number", "-created_at"]
        verbose_name = "Cover Letter Version"
        verbose_name_plural = "Cover Letter Versions"

    def __str__(self):
        return f"Cover Letter v{self.version_number} - {self.title} ({self.portfolio.name})"


class OptimizedResume(models.Model):
    """
    OptimizedResume model (Phase 9.3 MVP).
    Stores optimized resume versions linked to a portfolio draft.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="optimized_resumes")
    title = models.CharField(max_length=255)
    resume_data_json = models.JSONField(default=dict)
    version_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version_number", "-created_at"]
        verbose_name = "Optimized Resume"
        verbose_name_plural = "Optimized Resumes"

    def __str__(self):
        return f"{self.title} v{self.version_number} ({self.portfolio.name})"






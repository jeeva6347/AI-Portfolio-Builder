from django.urls import path
from . import views

app_name = "portfolio"

urlpatterns = [
    # Portfolios list and creation
    path("", views.PortfolioListView.as_view(), name="list"),
    path("create/", views.PortfolioCreateView.as_view(), name="create"),

    # Builder & Update API
    path("builder/<int:pk>/", views.PortfolioBuilderView.as_view(), name="builder"),
    path("builder/<int:pk>/update-api/", views.PortfolioUpdateAPI.as_view(), name="update_api"),
    path("builder/<int:pk>/reorder/", views.PortfolioReorderAPI.as_view(), name="reorder_api"),
    path("builder/<int:pk>/duplicate-item/", views.PortfolioDuplicateItemAPI.as_view(), name="duplicate_item_api"),
    path("builder/<int:pk>/add-component/", views.PortfolioAddComponentAPI.as_view(), name="add_component_api"),
    path("builder/<int:pk>/versions/", views.PortfolioVersionListView.as_view(), name="version_list_api"),
    path("builder/<int:pk>/versions/<int:v_pk>/preview/", views.PortfolioVersionPreviewView.as_view(), name="version_preview_api"),
    path("builder/<int:pk>/versions/<int:v_pk>/restore/", views.PortfolioVersionRestoreAPI.as_view(), name="version_restore_api"),
    path("builder/<int:pk>/versions/compare/", views.PortfolioVersionCompareAPI.as_view(), name="version_compare_api"),

    # CRUD portfolio actions
    path("builder/<int:pk>/delete/", views.PortfolioDeleteView.as_view(), name="delete"),
    path("builder/<int:pk>/duplicate/", views.PortfolioDuplicateView.as_view(), name="duplicate"),
    path("builder/<int:pk>/publish/", views.PortfolioPublishView.as_view(), name="publish"),
    path("builder/<int:pk>/deploy/", views.PortfolioDeployView.as_view(), name="deploy_api"),
    path("builder/<int:pk>/ai-import/", views.PortfolioAIImportAPI.as_view(), name="ai_import_api"),
    path("builder/<int:pk>/ai-regenerate-section/", views.PortfolioAIRegenerateSectionAPI.as_view(), name="ai_regenerate_section_api"),
    path("builder/<int:pk>/ai-accept-section/", views.PortfolioAIAcceptSectionAPI.as_view(), name="ai_accept_section_api"),
    path("builder/<int:pk>/ai-analysis/", views.PortfolioAIAssistantAnalysisAPI.as_view(), name="ai_analysis_api"),
    path("builder/<int:pk>/resume-upload/", views.PortfolioResumeUploadAPI.as_view(), name="resume_upload_api"),
    path("builder/<int:pk>/resume-import/", views.PortfolioResumeImportAPI.as_view(), name="resume_import_api"),
    path("builder/<int:pk>/job-analysis/", views.PortfolioJobAnalysisAPI.as_view(), name="job_analysis_api"),
    path("builder/<int:pk>/job-apply/", views.PortfolioJobApplyAPI.as_view(), name="job_apply_api"),
    path("builder/<int:pk>/cover-letter/generate/", views.CoverLetterGenerateView.as_view(), name="cover_letter_generate_api"),
    path("builder/<int:pk>/cover-letter/save/", views.CoverLetterSaveView.as_view(), name="cover_letter_save_api"),
    path("builder/<int:pk>/cover-letter/history/", views.CoverLetterHistoryView.as_view(), name="cover_letter_history_api"),
    path("builder/<int:pk>/cover-letter/export/", views.CoverLetterExportView.as_view(), name="cover_letter_export_api"),
    path("resume/optimize/", views.ResumeOptimizeView.as_view(), name="resume_optimize_api"),
    path("resume/save/", views.ResumeSaveView.as_view(), name="resume_save_api"),
    path("export/", views.PortfolioExportView.as_view(), name="portfolio_export_api"),
    path("backup/export/", views.PortfolioBackupExportView.as_view(), name="portfolio_backup_export_api"),
    path("backup/import/", views.PortfolioBackupImportView.as_view(), name="portfolio_backup_import_api"),
    path("templates/", views.PortfolioTemplatesListView.as_view(), name="portfolio_templates_list_api"),
    path("template/change/", views.PortfolioChangeTemplateView.as_view(), name="portfolio_change_template_api"),
    path("seo/<int:pk>/", views.PortfolioSEOView.as_view(), name="portfolio_seo_api"),
    path("<int:pk>/deploy/", views.PortfolioDeployView.as_view(), name="deploy_api_short"),
    path("builder/<int:pk>/archive/", views.PortfolioArchiveView.as_view(), name="archive"),
    path("builder/<int:pk>/restore/", views.PortfolioRestoreView.as_view(), name="restore"),

    # Related items creation urls
    path("builder/<int:pk>/skills/create/", views.SkillCreateView.as_view(), name="skill_create"),
    path("builder/<int:pk>/projects/create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("builder/<int:pk>/experience/create/", views.ExperienceCreateView.as_view(), name="experience_create"),
    path("builder/<int:pk>/education/create/", views.EducationCreateView.as_view(), name="education_create"),
    path("builder/<int:pk>/certificates/create/", views.CertificateCreateView.as_view(), name="certificate_create"),
    path("builder/<int:pk>/services/create/", views.ServiceCreateView.as_view(), name="service_create"),
    path("builder/<int:pk>/testimonials/create/", views.TestimonialCreateView.as_view(), name="testimonial_create"),

    # Related items deletion urls (taking item pk)
    path("skills/<int:pk>/delete/", views.SkillDeleteView.as_view(), name="skill_delete"),
    path("projects/<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),
    path("experience/<int:pk>/delete/", views.ExperienceDeleteView.as_view(), name="experience_delete"),
    path("education/<int:pk>/delete/", views.EducationDeleteView.as_view(), name="education_delete"),
    path("certificates/<int:pk>/delete/", views.CertificateDeleteView.as_view(), name="certificate_delete"),
    path("services/<int:pk>/delete/", views.ServiceDeleteView.as_view(), name="service_delete"),
    path("testimonials/<int:pk>/delete/", views.TestimonialDeleteView.as_view(), name="testimonial_delete"),

    # Theme & Preview
    path("builder/<int:pk>/select-theme/", views.SelectThemeView.as_view(), name="select_theme"),
    path("use-theme/<int:theme_id>/", views.UseThemeFromMarketplaceView.as_view(), name="use_theme_marketplace"),
    path("preview/<int:pk>/", views.UserPortfolioPreview.as_view(), name="preview"),
]

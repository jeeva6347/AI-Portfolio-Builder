from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("billing/", views.BillingDashboardView.as_view(), name="billing"),
    path("checkout/", views.CheckoutSessionView.as_view(), name="checkout"),
    path("checkout/mock/", views.MockCheckoutView.as_view(), name="checkout_mock"),
    path("checkout/success/", views.PaymentSuccessView.as_view(), name="success"),
    path("checkout/failure/", views.PaymentFailureView.as_view(), name="failure"),
    path("cancel/", views.CancelSubscriptionView.as_view(), name="cancel"),
    
    path("admin/summary/", views.AdminBillingDashboardView.as_view(), name="admin_summary"),
]

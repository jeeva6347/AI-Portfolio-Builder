import uuid
from django.urls import reverse
from .base import BasePaymentProvider


class MockPaymentProvider(BasePaymentProvider):
    """
    Simulated implementation of a payment provider (Stripe equivalent).
    Logs pending transactions and creates local mock checkout URLs.
    """
    def create_checkout_session(self, user, plan, return_url: str) -> str:
        # Generate a unique transaction reference id
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        
        # Log transaction in pending state
        from payments.models import PaymentTransaction
        PaymentTransaction.objects.create(
            user=user,
            transaction_id=session_id,
            plan=plan,
            amount=plan.price,
            currency="USD",
            status=PaymentTransaction.Status.PENDING
        )
        
        # Construct target URL directing to the local simulation template
        mock_checkout_url = reverse("payments:checkout_mock")
        return f"{mock_checkout_url}?session_id={session_id}&plan_slug={plan.slug}"

    def cancel_subscription(self, provider_subscription_id: str) -> bool:
        # Cancellation simulation is always successful
        return True

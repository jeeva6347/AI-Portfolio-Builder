class BasePaymentProvider:
    """
    Abstract interface defining the blueprint for billing integrations.
    Allows seamlessly registering alternative providers (e.g. Stripe, PayPal, Lemon Squeezy).
    """
    def create_checkout_session(self, user, plan, return_url: str) -> str:
        """
        Initiates a checkout sequence and returns the redirect URL
        to the provider's payment interface.
        """
        raise NotImplementedError("Payment provider must implement create_checkout_session.")

    def cancel_subscription(self, provider_subscription_id: str) -> bool:
        """
        Cancels the active subscription on the remote payment gateway.
        """
        raise NotImplementedError("Payment provider must implement cancel_subscription.")

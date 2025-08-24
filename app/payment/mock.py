from __future__ import annotations
import uuid
from .base import PaymentProvider, PaymentInitiationResult


class MockPaymentProvider(PaymentProvider):
	"""Mock provider that confirms immediately.

	This keeps the code pluggable so a real MTN MoMo implementation can replace it later.
	"""

	def initiate_payment(self, *, phone_number: str, amount: int, narrative: str) -> PaymentInitiationResult:
		provider_ref = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
		# Simulate immediate success for the mock
		return PaymentInitiationResult(status="CONFIRMED", provider_reference=provider_ref, message="Mock payment confirmed")
from __future__ import annotations
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class PaymentInitiationResult:
	status: str
	provider_reference: str | None
	message: str | None = None


class PaymentProvider(ABC):
	"""Abstract payment provider interface to support pluggable implementations."""

	@abstractmethod
	def initiate_payment(self, *, phone_number: str, amount: int, narrative: str) -> PaymentInitiationResult:
		"""Initiate a payment collection request.

		Args:
			phone_number: MSISDN in international format, e.g., 2567XXXXXXXX
			amount: Amount in minor units (e.g., cents)
			narrative: Description to show the payer

		Returns:
			PaymentInitiationResult indicating status and provider reference
		"""
		raise NotImplementedError
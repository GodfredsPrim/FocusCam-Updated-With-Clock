from __future__ import annotations
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import UssdSession, Vote, Payment, PaymentStatus, get_db
from ..payment.mock import MockPaymentProvider

router = APIRouter(prefix="/ussd", tags=["ussd"])

# Fixed voting fee in minor units (e.g., cents)
VOTE_FEE_MINOR = 100


def _get_input_token(text: Optional[str]) -> Optional[str]:
	if text is None:
		return None
	text = text.strip()
	if not text:
		return None
	# Many USSD gateways concatenate inputs with '*'
	parts = text.split("*")
	return parts[-1].strip() if parts else None


@router.post("", response_class=PlainTextResponse)
async def ussd_entry(request: Request, response: Response, db: Session = Depends(get_db)) -> str:
	"""Handle USSD requests.

	Accepts form or JSON with fields like: sessionId, phoneNumber, text, serviceCode.
	Responds with 'CON ' to continue or 'END ' to finish.
	"""
	# Parse body as form first, then JSON
	form = await request.form() if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") else None
	payload = {}
	if form:
		payload = dict(form)
	else:
		try:
			payload = await request.json()
		except Exception:
			payload = {}

	session_id = payload.get("sessionId") or payload.get("session_id")
	phone_number = payload.get("phoneNumber") or payload.get("msisdn") or payload.get("phone")
	text = payload.get("text") or payload.get("userInput")
	user_input = _get_input_token(text)

	if not session_id or not phone_number:
		response.status_code = 400
		return "END Invalid request"

	# Normalize phone: remove spaces, dashes
	phone_number = phone_number.replace(" ", "").replace("-", "")

	# Ensure session exists
	session_obj = db.execute(select(UssdSession).where(UssdSession.session_id == session_id)).scalar_one_or_none()
	if session_obj is None:
		session_obj = UssdSession(
			session_id=session_id,
			phone_number=phone_number,
			state="MENU",
			is_active=True,
		)
		db.add(session_obj)
		db.commit()
		db.refresh(session_obj)

	# Prevent actions on closed sessions
	if not session_obj.is_active:
		return "END Session closed."

	# If phone already voted, short-circuit unless they are just starting
	existing_vote = db.execute(select(Vote).where(Vote.phone_number == phone_number)).scalar_one_or_none()
	if existing_vote and session_obj.state not in {"END"}:
		session_obj.is_active = False
		session_obj.state = "END"
		session_obj.updated_at = datetime.utcnow()
		db.commit()
		return "END You have already voted. Thank you."

	# State machine
	if session_obj.state == "MENU":
		if user_input is None:
			return "CON 1. Vote for Candidate A\n2. Vote for Candidate B\n3. Exit"
		if user_input == "1":
			session_obj.selected_candidate = "A"
			session_obj.state = "CONFIRM"
			session_obj.updated_at = datetime.utcnow()
			db.commit()
			return f"CON You selected Candidate A. Payment required: {VOTE_FEE_MINOR} units.\n1. Confirm\n2. Cancel"
		if user_input == "2":
			session_obj.selected_candidate = "B"
			session_obj.state = "CONFIRM"
			session_obj.updated_at = datetime.utcnow()
			db.commit()
			return f"CON You selected Candidate B. Payment required: {VOTE_FEE_MINOR} units.\n1. Confirm\n2. Cancel"
		if user_input == "3":
			session_obj.is_active = False
			session_obj.state = "END"
			session_obj.updated_at = datetime.utcnow()
			db.commit()
			return "END Goodbye."
		# Unknown input -> redisplay menu
		return "CON Invalid option.\n1. Vote for Candidate A\n2. Vote for Candidate B\n3. Exit"

	elif session_obj.state == "CONFIRM":
		if user_input == "1":
			# Initiate payment
			provider = MockPaymentProvider()
			result = provider.initiate_payment(
				phone_number=phone_number,
				amount=VOTE_FEE_MINOR,
				narrative=f"Vote for {session_obj.selected_candidate}",
			)

			payment = Payment(
				phone_number=phone_number,
				amount=VOTE_FEE_MINOR,
				status=result.status if result.status in {PaymentStatus.PENDING, PaymentStatus.CONFIRMED, PaymentStatus.FAILED} else PaymentStatus.PENDING,
				provider="mock",
				provider_reference=result.provider_reference,
			)
			db.add(payment)
			db.commit()
			db.refresh(payment)

			vote_recorded = False
			message_suffix = ""
			if payment.status == PaymentStatus.CONFIRMED:
				# Create the vote if not exists
				try:
					vote = Vote(phone_number=phone_number, candidate=session_obj.selected_candidate, payment_id=payment.id)
					db.add(vote)
					db.commit()
					vote_recorded = True
				except IntegrityError:
					db.rollback()
					message_suffix = " Already voted."

			session_obj.is_active = False
			session_obj.state = "END"
			session_obj.updated_at = datetime.utcnow()
			db.commit()

			if vote_recorded:
				return f"END Payment received. Your vote for Candidate {session_obj.selected_candidate} has been recorded."
			if payment.status == PaymentStatus.PENDING:
				return "END Payment initiated. Your vote will be recorded once payment is confirmed."
			return f"END Payment failed.{message_suffix}"

		elif user_input == "2":
			session_obj.is_active = False
			session_obj.state = "END"
			session_obj.updated_at = datetime.utcnow()
			db.commit()
			return "END Cancelled."
		else:
			return "CON Invalid option.\n1. Confirm\n2. Cancel"

	# Fallback
	session_obj.is_active = False
	session_obj.state = "END"
	session_obj.updated_at = datetime.utcnow()
	db.commit()
	return "END Session ended."
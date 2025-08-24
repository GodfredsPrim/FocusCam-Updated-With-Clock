from datetime import datetime
from typing import Optional

from sqlalchemy import (
	Column,
	DateTime,
	Integer,
	String,
	Boolean,
	ForeignKey,
	UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, Session

from .database import Base, SessionLocal


class PaymentStatus:
	PENDING = "PENDING"
	CONFIRMED = "CONFIRMED"
	FAILED = "FAILED"


class Payment(Base):
	__tablename__ = "payments"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	phone_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
	amount: Mapped[int] = mapped_column(Integer, nullable=False)  # in minor units (e.g., cents)
	status: Mapped[str] = mapped_column(String(16), default=PaymentStatus.PENDING, nullable=False, index=True)
	provider: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)
	provider_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

	vote = relationship("Vote", back_populates="payment", uselist=False)


class Vote(Base):
	__tablename__ = "votes"
	__table_args__ = (
		UniqueConstraint("phone_number", name="uq_votes_phone_number"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	phone_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
	candidate: Mapped[str] = mapped_column(String(1), nullable=False, index=True)  # 'A' or 'B'
	payment_id: Mapped[int] = mapped_column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

	payment = relationship("Payment", back_populates="vote")


class UssdSession(Base):
	__tablename__ = "ussd_sessions"

	# Note: session IDs come from the USSD gateway
	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
	phone_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
	state: Mapped[str] = mapped_column(String(32), default="START", nullable=False)
	selected_candidate: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# DB session dependency for FastAPI routes

def get_db() -> Session:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
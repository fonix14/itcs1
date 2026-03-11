from __future__ import annotations

import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import (
    String,
    DateTime,
    Enum,
    ForeignKey,
    Boolean,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------- USERS ----------------

class UserRole(str, enum.Enum):
    dispatcher = "dispatcher"
    manager = "manager"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ---------------- STORES ----------------

class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    assigned_user = relationship("User")


# ---------------- TASKS ----------------

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_task_id: Mapped[str] = mapped_column(String(100), nullable=False)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    sla: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    store = relationship("Store")

    __table_args__ = (
        UniqueConstraint("portal_task_id", name="uq_tasks_portal_task_id"),
    )


# ---------------- NOTIFICATION OUTBOX ----------------

class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="matrix")
    recipient_address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    template: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------- IMPORT TABLES ----------------

class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    profile_id: Mapped[str] = mapped_column(String(80), nullable=False, default="default")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_ratio: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    seen_tasks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UploadMetrics(Base):
    __tablename__ = "upload_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=False, unique=True)
    baseline_seen: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    abs_drop: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rel_drop: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    coverage_drop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ---------------- ANOMALIES ----------------

class AnomalySeverity(str, enum.Enum):
    critical = "critical"
    major = "major"
    minor = "minor"


class AnomalyStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anomaly_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AnomalySeverity] = mapped_column(Enum(AnomalySeverity, name="anomaly_severity"), nullable=False)
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus, name="anomaly_status"),
        nullable=False,
        default=AnomalyStatus.open,
    )
    related_upload_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    related_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ---------------- HEALTH STATE (for notifier compatibility) ----------------

class HealthState(Base):
    __tablename__ = "health_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    last_trust_level: Mapped[str] = mapped_column(String(16), nullable=False, default="GREEN")
    last_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    last_notified_trust_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_daily_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# ---------------- DEVICE SUBSCRIPTIONS ----------------

class DeviceSubscription(Base):
    __tablename__ = "device_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user = relationship("User")

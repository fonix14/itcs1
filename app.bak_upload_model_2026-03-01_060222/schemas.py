from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class Me(BaseModel):
    user_id: UUID
    role: str


class StoreOut(BaseModel):
    id: UUID
    store_no: str
    name: Optional[str] = None
    assigned_user_id: Optional[UUID] = None


class TaskOut(BaseModel):
    id: UUID
    portal_task_id: str
    store_id: UUID
    status: str
    sla: Optional[str] = None
    last_seen_at: datetime


class AcceptIn(BaseModel):
    comment: Optional[str] = Field(default=None, max_length=2000)


class TaskInternalOut(BaseModel):
    task_id: UUID
    accepted_at: Optional[datetime] = None
    accepted_by_user_id: Optional[UUID] = None
    last_comment: Optional[str] = None
    updated_at: datetime


class UploadOut(BaseModel):
    id: UUID
    file_name: str
    file_hash: str
    profile_id: str
    uploaded_at: datetime
    total_rows: int
    valid_rows: int
    invalid_rows: int
    invalid_ratio: float
    seen_tasks_count: int


class ImportReport(BaseModel):
    upload: UploadOut
    anomalies_created: int
    trust_level: str
    trust_reasons: list[str]
    idempotent: bool = False


class AnomalyOut(BaseModel):
    id: UUID
    anomaly_type: str
    severity: str
    status: str
    related_upload_id: Optional[UUID] = None
    related_task_id: Optional[UUID] = None
    details: dict
    due_at: Optional[datetime] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class TrustSummary(BaseModel):
    trust_level: str
    reasons: list[str]
    last_import_at: Optional[datetime] = None
    invalid_ratio: Optional[float] = None
    coverage_drop: Optional[bool] = None
    pending_anomalies: int


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str

class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys

class OutboxItemOut(BaseModel):
    id: UUID
    kind: str
    user_id: UUID
    payload: dict
    status: str
    attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None

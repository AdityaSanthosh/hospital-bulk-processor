"""SQLite-backed job repository (SQLAlchemy)

Drop-in replacement for the in-memory JobRepository. Exposes the same API used
throughout the codebase:

- create(total_hospitals) -> Job
- get(job_id) -> Optional[Job]
- get_or_raise(job_id) -> Job
- update_status(job_id, status) -> None
- set_result(job_id, result) -> None
- set_error(job_id, error) -> None
- get_all() -> Dict[str, Job]

Notes:
- Uses a local SQLite file by default (./jobs.db). Override with
  `sqlite_db_url` setting in `app/config.py` or via environment variable.
- Keeps transactions short and commits per operation to reduce lock contention.
- For production/high-concurrency use a client-server DB (Postgres, etc.).
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, sessionmaker

from app.config import settings
from app.domain.exceptions import JobNotFoundException
from app.domain.schemas import BulkCreateResponse, JobStatus

logger = logging.getLogger(__name__)

# Database URL - allow override from settings; fall back to a local file
DATABASE_URL = getattr(settings, "sqlite_db_url", "sqlite:///./jobs.db")

# Create engine - allow multiple processes to connect (check_same_thread False)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)

Base = declarative_base()


class JobModel(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_hospitals: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_hospitals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_hospitals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # store JSON string
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# Ensure table exists (suitable for dev; use migrations for production)
Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class Job:
    """Lightweight Job object used by the rest of the app (mimics previous in-memory model)"""

    def __init__(
        self,
        job_id: str,
        status: JobStatus,
        total_hospitals: int,
        processed_hospitals: int = 0,
        failed_hospitals: int = 0,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[BulkCreateResponse] = None,
        error: Optional[str] = None,
    ):
        self.job_id = job_id
        self.status = status
        self.total_hospitals = total_hospitals
        self.processed_hospitals = processed_hospitals
        self.failed_hospitals = failed_hospitals
        self.started_at = started_at
        self.completed_at = completed_at
        self.result = result
        self.error = error

    @property
    def progress_percentage(self) -> float:
        if self.total_hospitals == 0:
            return 0.0
        return round((self.processed_hospitals / self.total_hospitals) * 100, 2)

    @property
    def processing_time_seconds(self) -> Optional[float]:
        if not self.started_at:
            return None
        end = self.completed_at or datetime.now(timezone.utc)
        return round((end - self.started_at).total_seconds(), 2)


class JobRepository:
    """SQLite-backed repository implementation"""

    def __init__(self):
        logger.info("JobRepository initialized (sqlite)")

    def _row_to_job(self, row: JobModel) -> Job:
        result_obj: Optional[BulkCreateResponse] = None
        if row.result:
            try:
                # Prefer pydantic v2 JSON helper
                result_obj = BulkCreateResponse.model_validate_json(row.result)
            except Exception:
                try:
                    parsed = json.loads(row.result)
                    result_obj = BulkCreateResponse.model_validate(parsed)
                except Exception:
                    result_obj = None

        return Job(
            job_id=row.job_id,
            status=JobStatus(row.status),
            total_hospitals=row.total_hospitals,
            processed_hospitals=row.processed_hospitals,
            failed_hospitals=row.failed_hospitals,
            started_at=row.started_at,
            completed_at=row.completed_at,
            result=result_obj,
            error=row.error,
        )

    def create(self, total_hospitals: int) -> Job:
        job_id = str(uuid.uuid4())
        with session_scope() as s:
            jm = JobModel(
                job_id=job_id,
                status=JobStatus.PENDING.value,
                total_hospitals=total_hospitals,
                processed_hospitals=0,
                failed_hospitals=0,
                started_at=None,
                completed_at=None,
                result=None,
                error=None,
            )
            s.add(jm)
            try:
                s.flush()
            except IntegrityError:
                s.rollback()
                raise
        return Job(
            job_id=job_id, status=JobStatus.PENDING, total_hospitals=total_hospitals
        )

    def get(self, job_id: str) -> Optional[Job]:
        with session_scope() as s:
            row = s.get(JobModel, job_id)
            if not row:
                return None
            return self._row_to_job(row)

    def get_or_raise(self, job_id: str) -> Job:
        job = self.get(job_id)
        if not job:
            raise JobNotFoundException(f"Job {job_id} not found")
        return job

    def update_status(self, job_id: str, status: JobStatus) -> None:
        with session_scope() as s:
            jm = s.get(JobModel, job_id)
            if not jm:
                raise JobNotFoundException(f"Job {job_id} not found")
            jm.status = status.value
            # set started_at when transitioning to PROCESSING
            if status == JobStatus.PROCESSING and jm.started_at is None:
                jm.started_at = datetime.now(timezone.utc)
            # set completed_at when finishing
            if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                if jm.started_at is None:
                    jm.started_at = datetime.now(timezone.utc)
                jm.completed_at = datetime.now(timezone.utc)
            s.add(jm)

    def set_result(self, job_id: str, result: BulkCreateResponse) -> None:
        serialized = result.model_dump_json()
        with session_scope() as s:
            jm = s.get(JobModel, job_id)
            if not jm:
                raise JobNotFoundException(f"Job {job_id} not found")
            jm.result = serialized
            jm.processed_hospitals = result.processed_hospitals
            jm.failed_hospitals = result.failed_hospitals
            s.add(jm)

    def set_error(self, job_id: str, error: str) -> None:
        with session_scope() as s:
            jm = s.get(JobModel, job_id)
            if not jm:
                raise JobNotFoundException(f"Job {job_id} not found")
            jm.error = error
            jm.status = JobStatus.FAILED.value
            if jm.started_at is None:
                jm.started_at = datetime.now(timezone.utc)
            jm.completed_at = datetime.now(timezone.utc)
            s.add(jm)

    def get_all(self) -> Dict[str, Job]:
        out: Dict[str, Job] = {}
        with session_scope() as s:
            rows = s.execute(select(JobModel)).scalars().all()
            for r in rows:
                out[r.job_id] = self._row_to_job(r)
        return out


# global instance used by the rest of the codebase
job_repository = JobRepository()

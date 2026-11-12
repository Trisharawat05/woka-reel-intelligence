import os
import re
import json
import uuid
import shutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

logger = logging.getLogger(__name__)

import socket
import ipaddress
from urllib.parse import urlparse

from app.models.reel_intelligence import (
    ReelAnalysisJob,
    ReelMediaAsset,
    ReelMetricSnapshot,
    ReelReport,
    ReelComparison
)
from app.models.instagram import InstagramAccount
from app.models.analytics import CreatorAnalytics
from app.services.video_intelligence.pipeline import run_video_intelligence_pipeline
from app.services.reel_analytics_service import calculate_reel_performance_metrics
from app.services.reel_ai_diagnosis_service import generate_ai_diagnosis_report
from app.services.subscription_service import check_and_increment_ai_quota
from app.services.instagram_service import verify_connected_account_media_ownership

STORAGE_BASE_DIR = "media_storage"
ALLOWED_VIDEO_MIMES = ["video/mp4", "video/quicktime", "video/webm", "video/x-m4v"]
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

ACTIVE_ANALYSIS_STATUSES = (
    "QUEUED",
    "INGESTING",
    "PROCESSING_VIDEO",
    "ANALYZING_METRICS",
    "GENERATING_AI_REPORT",
)

_REPORT_UPDATABLE_FIELDS = (
    "title",
    "caption",
    "analysis_mode",
    "thumbnail_url",
    "duration_seconds",
    "creative_quality_score",
    "performance_score",
    "growth_conversion_score",
    "viral_potential_estimate",
    "score_breakdown_json",
    "calculated_metrics_json",
    "video_intelligence_json",
    "timeline_findings_json",
    "prioritized_action_plan_json",
    "creative_alternatives_json",
    "provenance_json",
)

_INTERNAL_ERROR_PATTERNS = (
    "psycopg2",
    "sqlite3",
    "sqlalchemy",
    "uniqueviolation",
    "integrityerror",
    "operationalerror",
    "duplicate key",
    "unique constraint",
    "foreign key",
    "[sql:",
    "[parameters:",
    "traceback (most recent call last)",
    "select ",
    "insert into ",
    "update ",
    "delete from ",
    "postgresql://",
    "sqlite:///",
)

DEFAULT_FRIENDLY_ANALYSIS_ERROR = (
    "Reel analysis could not be completed right now. Please click Retry Analysis to try again."
)
DATABASE_FRIENDLY_ANALYSIS_ERROR = (
    "We couldn't save your Reel analysis report right now. Please click Retry Analysis to try again."
)


def sanitize_job_error_message(exc: Exception) -> str:
    """
    Converts internal/database exceptions into user-friendly Analysis Notice text
    without exposing SQL queries, constraint names, stack traces, or credentials.
    """
    from app.services.instagram_service import MetaAPIError, sanitize_meta_error_message

    if isinstance(exc, PermissionError):
        return "You are not authorized to access or update this analysis report."
    if isinstance(exc, SQLAlchemyError):
        return DATABASE_FRIENDLY_ANALYSIS_ERROR

    raw_message = sanitize_meta_error_message(str(exc)).strip()
    lowered = raw_message.lower()
    if not raw_message or any(pattern in lowered for pattern in _INTERNAL_ERROR_PATTERNS):
        if "constraint" in lowered or "sql" in lowered or "duplicate key" in lowered:
            return DATABASE_FRIENDLY_ANALYSIS_ERROR
        return DEFAULT_FRIENDLY_ANALYSIS_ERROR

    if isinstance(exc, (MetaAPIError, ValueError)):
        if len(raw_message) > 280 or "c:\\" in lowered or "/users/" in lowered or "\n" in raw_message:
            return DEFAULT_FRIENDLY_ANALYSIS_ERROR
        return raw_message

    return DEFAULT_FRIENDLY_ANALYSIS_ERROR


def get_job_report_for_workspace(
    db: Session,
    job_id: str,
    workspace_id: str,
    for_update: bool = False,
) -> Optional[ReelReport]:
    """Fetches the single ReelReport for a job while verifying workspace ownership."""
    query = db.query(ReelReport).filter(
        ReelReport.job_id == job_id,
        ReelReport.workspace_id == workspace_id,
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def _is_reel_report_job_id_unique_violation(exc: IntegrityError) -> bool:
    """Detects PostgreSQL (23505) and SQLite unique violations on reel_reports.job_id."""
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None)
    diag = getattr(orig, "diag", None)
    constraint_name = (getattr(diag, "constraint_name", None) or "").lower()
    msg = f"{orig or ''} {exc}".lower()

    if constraint_name == "reel_reports_job_id_key":
        return True
    if pgcode == "23505" and ("reel_reports" in msg or "job_id" in msg or not constraint_name):
        return True
    if "reel_reports_job_id_key" in msg or "reel_reports.job_id" in msg:
        return True
    if "unique constraint" in msg and "job_id" in msg:
        return True
    return False


def _apply_report_fields(report: ReelReport, report_fields: Dict[str, Any]) -> None:
    for field in _REPORT_UPDATABLE_FIELDS:
        if field in report_fields:
            setattr(report, field, report_fields[field])
    report.updated_at = datetime.now(timezone.utc)


def upsert_reel_report_for_job(
    db: Session,
    job: ReelAnalysisJob,
    report_fields: Dict[str, Any],
    workspace_id: Optional[str] = None,
) -> ReelReport:
    """
    Transactionally inserts or updates the single ReelReport for a job.

    - Enforces strict workspace_id ownership on every lookup and write.
    - Uses a SAVEPOINT (begin_nested) around INSERT so concurrent PostgreSQL/SQLite
      UniqueViolation conflicts on reel_reports_job_id_key recover cleanly without
      aborting the session transaction, updating the existing row instead.
    - Links job.report_id and marks job COMPLETED atomically in the same commit.
    """
    expected_workspace_id = workspace_id if workspace_id is not None else (job.workspace_id if job else None)
    if not job or not expected_workspace_id or job.workspace_id != expected_workspace_id:
        raise PermissionError("Workspace ownership mismatch for Reel analysis job.")
    target_job_id = job.id

    report = get_job_report_for_workspace(
        db, target_job_id, expected_workspace_id, for_update=True
    )
    if report is not None:
        _apply_report_fields(report, report_fields)
        db.flush()
    else:
        foreign_owner = db.query(ReelReport.workspace_id).filter(
            ReelReport.job_id == target_job_id,
            ReelReport.workspace_id != expected_workspace_id,
        ).first()
        if foreign_owner is not None:
            raise PermissionError("Existing report belongs to a different workspace.")

        clean_payload = {k: report_fields[k] for k in _REPORT_UPDATABLE_FIELDS if k in report_fields}
        try:
            with db.begin_nested():
                report = ReelReport(
                    workspace_id=expected_workspace_id,
                    job_id=target_job_id,
                    **clean_payload,
                )
                db.add(report)
                db.flush()
        except IntegrityError as exc:
            if not _is_reel_report_job_id_unique_violation(exc):
                raise
            logger.warning(
                "Concurrent ReelReport unique conflict handled for job_id=%s workspace_id=%s; updating existing report",
                target_job_id,
                expected_workspace_id,
            )
            db.expire_all()
            report = get_job_report_for_workspace(
                db, target_job_id, expected_workspace_id, for_update=True
            )
            if report is None:
                foreign_owner = db.query(ReelReport.workspace_id).filter(
                    ReelReport.job_id == target_job_id,
                    ReelReport.workspace_id != expected_workspace_id,
                ).first()
                if foreign_owner is not None:
                    raise PermissionError("Existing report belongs to a different workspace.") from exc
                # Defensive snapshot refresh for stricter isolation levels (e.g. REPEATABLE READ)
                db.rollback()
                report = get_job_report_for_workspace(
                    db, target_job_id, expected_workspace_id, for_update=True
                )
                if report is None:
                    raise
            _apply_report_fields(report, report_fields)
            db.flush()

    job_row = (
        db.query(ReelAnalysisJob)
        .filter(
            ReelAnalysisJob.id == target_job_id,
            ReelAnalysisJob.workspace_id == expected_workspace_id,
        )
        .with_for_update()
        .first()
    )
    if not job_row:
        raise PermissionError("Workspace ownership mismatch for Reel analysis job.")

    job_row.report_id = report.id
    job_row.status = "COMPLETED"
    job_row.progress_percent = 100
    job_row.stage_message = "Analysis finalized and ready for review"
    job_row.error_message = None
    job_row.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    db.refresh(job_row)
    return report


def should_schedule_analysis_job(db: Session, job: ReelAnalysisJob, created: bool) -> bool:
    """
    Determines whether a submitted/reused job requires background pipeline execution.
    Completed jobs with an existing report reuse that report without re-running.
    """
    if created:
        return True

    if job.status == "COMPLETED":
        existing_report = get_job_report_for_workspace(db, job.id, job.workspace_id)
        if existing_report is not None:
            repaired = False
            if job.report_id != existing_report.id:
                job.report_id = existing_report.id
                repaired = True
            if job.error_message is not None:
                job.error_message = None
                repaired = True
            if repaired:
                db.commit()
                db.refresh(job)
            return False

        # Defensive recovery if a completed placeholder job (e.g. insights sync) has no report yet
        foreign_owner = db.query(ReelReport.workspace_id).filter(
            ReelReport.job_id == job.id,
            ReelReport.workspace_id != job.workspace_id,
        ).first()
        if foreign_owner is not None:
            return False
        job.status = "QUEUED"
        job.progress_percent = 5
        job.stage_message = "Queued for AI Reel report generation"
        job.error_message = None
        db.commit()
        db.refresh(job)
        return True

    if job.status in ACTIVE_ANALYSIS_STATUSES:
        return False

    return True


def is_ip_private_or_restricted(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def validate_video_file_magic_bytes(header_bytes: bytes) -> bool:
    """Inspects binary file signature to verify video container and reject executables."""
    if not header_bytes or len(header_bytes) < 4:
        return False
    
    # Reject dangerous executable formats immediately
    if header_bytes.startswith(b"MZ"):  # Windows PE executable
        return False
    if header_bytes.startswith(b"\x7fELF"):  # Linux ELF executable
        return False
    if header_bytes.startswith(b"#!/") or header_bytes.startswith(b"<?php"):
        return False
    if b"<html" in header_bytes.lower() or b"<!doctype" in header_bytes.lower():
        return False

    # MP4 / M4V / MOV signature: typically contains 'ftyp' in first 32 bytes or 'moov' / 'mdat' / 'wide'
    if b"ftyp" in header_bytes[:32] or b"moov" in header_bytes[:32] or b"mdat" in header_bytes[:32] or b"wide" in header_bytes[:32]:
        return True

    # WebM / MKV starts with \x1a\x45\xdf\xa3
    if header_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    return True  # Fallback for other valid raw video formats


def validate_instagram_reel_url(url: str) -> Dict[str, Any]:
    """Validates Instagram Reel / Post URLs and extracts media shortcode with SSRF protection."""
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid video URL must be provided."
        )
    
    clean_url = url.strip()
    
    try:
        parsed = urlparse(clean_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed URL provided."
        )

    if parsed.scheme not in ["http", "https"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid URL scheme. Only HTTP/HTTPS URLs are supported."
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL hostname is missing or invalid."
        )

    # SSRF Protection: verify host is not private/loopback/link-local/metadata
    restricted_hostnames = {
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "metadata.google.internal", "instance-data", "metadata"
    }
    if (
        hostname in restricted_hostnames
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or (hostname.endswith(".nip.io") and any(is_ip_private_or_restricted(part) for part in hostname.split(".")))
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Access to private or local network addresses is forbidden."
        )

    # If hostname is an IP address directly, check if private
    if is_ip_private_or_restricted(hostname):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Access to private or internal network addresses is forbidden."
        )

    # DNS Resolution Check: Verify hostname does not resolve to private/loopback/metadata IP
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if is_ip_private_or_restricted(ip_str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Access to private, link-local, or metadata network addresses is forbidden."
                )
    except socket.gaierror:
        # Hostname cannot be resolved via DNS (offline test environment)
        pass

    # Matches instagram.com/reel/CODE/, instagram.com/p/CODE/, or direct video files (.mp4/.mov)
    ig_pattern = r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:reel|p)\/([a-zA-Z0-9_-]+)"
    match = re.search(ig_pattern, clean_url)
    
    if match:
        shortcode = match.group(1)
        return {"is_instagram": True, "shortcode": shortcode, "url": clean_url}
    
    # Check for direct video links
    if clean_url.endswith((".mp4", ".mov", ".webm", ".m4v")) or "video" in clean_url.lower():
        return {"is_instagram": False, "shortcode": None, "url": clean_url}
        
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Invalid URL format. Please provide an Instagram Reel link (e.g. https://www.instagram.com/reel/...) or video URL."
    )


def create_or_get_url_analysis_job(
    db: Session,
    workspace_id: str,
    url: str,
    declared_metrics: Optional[Dict[str, Any]] = None
) -> Tuple[ReelAnalysisJob, bool]:
    """Creates or returns an idempotent active/completed analysis job for a public Reel URL."""
    validated = validate_instagram_reel_url(url)

    # Idempotency check: Return existing active or completed job if identical URL was recently submitted
    existing_job = db.query(ReelAnalysisJob).filter(
        ReelAnalysisJob.workspace_id == workspace_id,
        ReelAnalysisJob.source_url == validated["url"],
        ReelAnalysisJob.status.in_([*ACTIVE_ANALYSIS_STATUSES, "COMPLETED"])
    ).order_by(ReelAnalysisJob.created_at.desc()).first()
    if existing_job:
        return existing_job, False

    # Enforce AI analysis quota
    if not check_and_increment_ai_quota(db, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly Reel AI analysis quota exceeded for your workspace plan. Please upgrade your subscription."
        )

    job = ReelAnalysisJob(
        workspace_id=workspace_id,
        analysis_mode="PUBLIC_URL",
        input_type="url",
        status="QUEUED",
        progress_percent=5,
        stage_message="Analysis job queued",
        source_url=validated["url"],
        source_media_id=validated.get("shortcode")
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, True


def create_url_analysis_job(
    db: Session,
    workspace_id: str,
    url: str,
    declared_metrics: Optional[Dict[str, Any]] = None
) -> ReelAnalysisJob:
    """Creates a new analysis job for a public Reel URL with quota check and idempotency."""
    job, _ = create_or_get_url_analysis_job(db, workspace_id, url, declared_metrics)
    return job


def create_upload_analysis_job(
    db: Session,
    workspace_id: str,
    file: UploadFile
) -> ReelAnalysisJob:
    """
    Validates and stores an uploaded video file, creating an analysis job with magic byte verification.

    Transaction & Quota Consistency Strategy:
    1. Pre-allocation validation: MIME format and header magic bytes are verified BEFORE quota consumption,
       preventing malicious or invalid payloads from draining creator quota.
    2. Compensation pattern: Quota increment is tracked via `quota_incremented`. If any subsequent failure
       occurs (100MB streaming size limit breach, network disconnect mid-stream, OS disk error, or database
       persistence failure), active transactions are rolled back, partial temporary files are deleted,
       and a compensating transaction refunds the allocated quota unit.
    3. Persistence atomicity: ReelMediaAsset and ReelAnalysisJob are flushed and committed in a single transaction
       to prevent orphaned assets or jobs.
    4. Limitation: In the event of an unrecoverable process crash or persistent database outage between the initial
       quota commit and compensation commit, reconciliation relies on regular subscription billing cycle resets.
    """
    if file.content_type not in ALLOWED_VIDEO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format: '{file.content_type}'. Supported formats: MP4, MOV, WebM."
        )

    # Read header for magic bytes inspection
    header_chunk = file.file.read(64)
    if not validate_video_file_magic_bytes(header_chunk):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file signature does not match a valid, safe video stream."
        )

    # Check quota only after verifying MIME and magic bytes (prevents malicious/invalid payloads from draining quota)
    if not check_and_increment_ai_quota(db, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly Reel AI analysis quota exceeded for your workspace plan. Please upgrade your subscription."
        )

    quota_incremented = True
    file_path: Optional[str] = None

    try:
        # Secure local workspace storage directory
        workspace_media_dir = os.path.join(STORAGE_BASE_DIR, workspace_id)
        os.makedirs(workspace_media_dir, exist_ok=True)

        safe_filename = f"{uuid.uuid4()}_{os.path.basename(file.filename or 'upload.mp4')}"
        file_path = os.path.join(workspace_media_dir, safe_filename)

        # Read and enforce file size constraint while streaming chunks to disk
        file_size = len(header_chunk)
        with open(file_path, "wb") as buffer:
            buffer.write(header_chunk)
            while chunk := file.file.read(1024 * 1024):  # 1MB chunks
                file_size += len(chunk)
                if file_size > MAX_VIDEO_SIZE_BYTES:
                    buffer.close()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {MAX_VIDEO_SIZE_BYTES // (1024 * 1024)}MB."
                    )
                buffer.write(chunk)

        # Atomic persistence of media asset and analysis job in a single commit
        media_asset = ReelMediaAsset(
            workspace_id=workspace_id,
            storage_path=file_path,
            original_filename=file.filename or "uploaded_reel.mp4",
            file_size_bytes=file_size,
            mime_type=file.content_type or "video/mp4",
            is_temporary=True
        )
        db.add(media_asset)
        db.flush()

        job = ReelAnalysisJob(
            workspace_id=workspace_id,
            analysis_mode="VIDEO_UPLOAD",
            input_type="upload",
            status="QUEUED",
            progress_percent=5,
            stage_message="Video uploaded and queued for processing",
            video_asset_id=media_asset.id
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    except Exception as exc:
        # 1. Roll back any active or pending database transaction
        try:
            db.rollback()
        except Exception as rb_err:
            logger.warning(f"Database rollback failed during upload cleanup: {rb_err}")

        # 2. Clean up partial or completed temporary file from disk on any failure
        if file_path:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError as fs_err:
                logger.warning(f"Failed to remove temporary upload file during error cleanup: {fs_err}")

        # 3. Exactly one quota refund attempt if quota was incremented
        if quota_incremented:
            quota_incremented = False  # Guard against double-refund
            try:
                from app.services.subscription_service import get_workspace_subscription
                sub = get_workspace_subscription(db, workspace_id)
                sub.ai_used_monthly = max(0, sub.ai_used_monthly - 1)
                db.commit()
            except Exception as refund_err:
                try:
                    db.rollback()
                except Exception:
                    pass
                logger.error(f"Failed to refund AI analysis quota after upload failure: {refund_err}")

        # 4. Preserve and re-raise the original exception
        raise exc


def resolve_authorized_thumbnail_path(workspace_id: str, filename: str) -> str:
    """
    Validates a thumbnail filename and resolves its absolute path strictly within
    the authorized workspace's thumbnail directory. Rejects path traversal attempts.
    """
    if (
        not filename
        or "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or filename in (".", "..")
        or os.path.basename(filename) != filename
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thumbnail filename.",
        )

    workspace_thumb_dir = os.path.realpath(
        os.path.join(STORAGE_BASE_DIR, workspace_id, "thumbnails")
    )
    candidate_path = os.path.realpath(os.path.join(workspace_thumb_dir, filename))

    if (
        os.path.commonpath([workspace_thumb_dir, candidate_path]) != workspace_thumb_dir
        or candidate_path == workspace_thumb_dir
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thumbnail path.",
        )

    if not os.path.isfile(candidate_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not found.",
        )

    return candidate_path


def create_or_get_connected_reel_analysis_job(
    db: Session,
    workspace_id: str,
    media_id: str,
    title: Optional[str] = None,
    caption: Optional[str] = None,
    media_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
) -> Tuple[ReelAnalysisJob, bool]:
    """
    Creates or returns an idempotent active/completed analysis job for a connected account Reel.
    Verifies authoritative media ownership and VIDEO/REELS eligibility before idempotency/quota allocation.
    Client-supplied metadata/URLs are ignored.
    """
    account = db.query(InstagramAccount).filter(
        InstagramAccount.workspace_id == workspace_id,
        InstagramAccount.is_connected == True
    ).first()

    # Verify media ownership & eligibility on the connected Instagram account
    authoritative_media = verify_connected_account_media_ownership(
        db=db,
        account=account,
        media_id=media_id,
        require_video_or_reel=True,
    )
    verified_media_id = str(authoritative_media["id"])
    authoritative_media_url = authoritative_media.get("media_url") or None

    # Idempotency check: Return existing active or completed job if identical media was recently submitted
    existing_job = db.query(ReelAnalysisJob).filter(
        ReelAnalysisJob.workspace_id == workspace_id,
        ReelAnalysisJob.source_media_id == verified_media_id,
        ReelAnalysisJob.status.in_([*ACTIVE_ANALYSIS_STATUSES, "COMPLETED"])
    ).order_by(ReelAnalysisJob.created_at.desc()).first()
    if existing_job:
        return existing_job, False

    # Quota check
    if not check_and_increment_ai_quota(db, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly Reel AI analysis quota exceeded for your workspace plan. Please upgrade your subscription."
        )

    job = ReelAnalysisJob(
        workspace_id=workspace_id,
        analysis_mode="CONNECTED_ACCOUNT",
        input_type="connected_account",
        status="QUEUED",
        progress_percent=5,
        stage_message="Queued for connected account analysis",
        source_media_id=verified_media_id,
        source_url=authoritative_media_url
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    # Cache authoritative Meta fields transiently on the in-memory ORM instance for immediate background task
    setattr(job, "_authoritative_media_cache", authoritative_media)
    return job, True


def create_connected_reel_analysis_job(
    db: Session,
    workspace_id: str,
    media_id: str,
    title: Optional[str] = None,
    caption: Optional[str] = None,
    media_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None
) -> ReelAnalysisJob:
    """
    Creates an analysis job for a connected professional account Reel.
    Verifies authoritative media ownership and VIDEO/REELS eligibility before idempotency/quota allocation.
    Client-supplied metadata/URLs are ignored.
    """
    job, _ = create_or_get_connected_reel_analysis_job(
        db=db,
        workspace_id=workspace_id,
        media_id=media_id,
        title=title,
        caption=caption,
        media_url=media_url,
        thumbnail_url=thumbnail_url,
    )
    return job


def execute_reel_analysis(
    db: Session,
    job_id: str,
    declared_metrics: Optional[Dict[str, Any]] = None,
    workspace_id: Optional[str] = None,
    authoritative_media_override: Optional[Dict[str, Any]] = None,
):
    """
    Executes the multi-stage analysis pipeline synchronously or as a background task.
    Reuses existing reports for already-completed jobs and updates reports idempotently on retry.
    """
    query = db.query(ReelAnalysisJob).filter(ReelAnalysisJob.id == job_id)
    if workspace_id is not None:
        query = query.filter(ReelAnalysisJob.workspace_id == workspace_id)
    job = query.first()
    if not job:
        if workspace_id is not None:
            exists_other = db.query(ReelAnalysisJob.id).filter(ReelAnalysisJob.id == job_id).first()
            if exists_other is not None:
                raise PermissionError("Workspace ownership verification failed for Reel analysis job.")
        return None

    existing_report = get_job_report_for_workspace(db, job.id, job.workspace_id)
    if job.status == "COMPLETED" and existing_report is not None:
        repaired = False
        if job.report_id != existing_report.id:
            job.report_id = existing_report.id
            repaired = True
        if job.error_message is not None:
            job.error_message = None
            repaired = True
        if repaired:
            db.commit()
            db.refresh(job)
        return existing_report

    try:
        # Stage 1: Ingestion (15%)
        job.status = "INGESTING"
        job.progress_percent = 15
        job.stage_message = "Ingesting media stream and verifying authoritative metadata"
        db.commit()

        video_path = None
        original_filename = None
        if job.video_asset_id:
            asset = db.query(ReelMediaAsset).filter(
                ReelMediaAsset.id == job.video_asset_id,
                ReelMediaAsset.workspace_id == job.workspace_id,
            ).first()
            if asset:
                video_path = asset.storage_path
                original_filename = asset.original_filename

        account: Optional[InstagramAccount] = None
        media_meta: Dict[str, Any] = authoritative_media_override or {}
        is_sandbox_account = False

        if job.analysis_mode == "CONNECTED_ACCOUNT":
            account = db.query(InstagramAccount).filter(
                InstagramAccount.workspace_id == job.workspace_id,
                InstagramAccount.is_connected == True
            ).first()
            if not account:
                raise ValueError("No active connected Instagram account found for this workspace.")
            is_sandbox_account = bool(account.is_sandbox)

            if not media_meta and job.source_media_id:
                if is_sandbox_account:
                    from app.services.instagram_service import get_sandbox_media_catalog
                    catalog = get_sandbox_media_catalog(account.ig_user_id, include_non_video=True)
                    media_meta = next((m for m in catalog if str(m.get("id", "")) == job.source_media_id), {})
                else:
                    media_meta = verify_connected_account_media_ownership(
                        db=db,
                        account=account,
                        media_id=job.source_media_id,
                        require_video_or_reel=False,
                    )

        real_caption: Optional[str] = None
        real_title: str = f"Reel Analysis — {job.source_media_id or 'Uploaded Video'}"
        authoritative_thumb_url: Optional[str] = None

        if job.analysis_mode == "CONNECTED_ACCOUNT":
            real_caption = (media_meta.get("caption") or "").strip() or None
            candidate_title = (media_meta.get("title") or "").strip()
            if not candidate_title and real_caption:
                candidate_title = real_caption.split("\n")[0][:70].strip()
            real_title = candidate_title or f"Connected Reel — {job.source_media_id or 'Instagram'}"
            authoritative_thumb_url = (media_meta.get("thumbnail_url") or "").strip() or None
        elif job.analysis_mode == "VIDEO_UPLOAD" and original_filename:
            real_title = f"Uploaded Reel — {original_filename[:60]}"
        elif job.analysis_mode == "PUBLIC_URL":
            real_title = f"Public Reel — {job.source_media_id}" if job.source_media_id else "Public Video Analysis"

        # Stage 2: Video & Frame Processing (45%)
        job.status = "PROCESSING_VIDEO"
        job.progress_percent = 45
        job.stage_message = "Analyzing video frames, visual pacing, and UI safe zones"
        db.commit()

        output_thumb_dir = os.path.join(STORAGE_BASE_DIR, job.workspace_id, "thumbnails")
        video_intel = run_video_intelligence_pipeline(
            video_path=video_path,
            media_url=media_meta.get("media_url") or job.source_url,
            caption=real_caption,
            title=real_title,
            output_thumbnail_dir=output_thumb_dir,
            allow_simulation=is_sandbox_account,
            source_identifier=job.source_media_id or job.source_url or job.id,
            original_filename=original_filename,
        )

        duration = video_intel.get("metadata", {}).get("duration_seconds")

        # Stage 3: Metric Analysis & Historical Baselines (70%)
        job.status = "ANALYZING_METRICS"
        job.progress_percent = 70
        job.stage_message = "Retrieving verified metrics and computing transparent ratios"
        db.commit()

        historical_analytics = db.query(CreatorAnalytics).filter(
            CreatorAnalytics.workspace_id == job.workspace_id
        ).order_by(CreatorAnalytics.snapshot_date.desc()).first()

        hist_avg_views: Optional[int] = None
        if historical_analytics and historical_analytics.reach_30d > 0 and historical_analytics.media_count > 0:
            hist_avg_views = int(historical_analytics.reach_30d / max(1, historical_analytics.media_count))

        views: Optional[int] = None
        reach: Optional[int] = None
        impressions: Optional[int] = None
        likes: Optional[int] = None
        comments: Optional[int] = None
        shares: Optional[int] = None
        saves: Optional[int] = None
        avg_watch: Optional[float] = None
        total_watch: Optional[float] = None
        follows: Optional[int] = None
        total_interactions: Optional[int] = None
        timestamped_retention_available = False

        if job.analysis_mode == "CONNECTED_ACCOUNT":
            assert account is not None
            if not is_sandbox_account:
                from app.services.instagram_service import fetch_media_insights
                from app.security import decrypt_token
                plain_token = decrypt_token(account.encrypted_access_token)
                if not plain_token:
                    raise ValueError("Stored Instagram access token is invalid or corrupted. Please reconnect.")

                # Live Meta Graph API query — never invent missing metrics
                insights = fetch_media_insights(plain_token, job.source_media_id)
                views = int(insights["views"]) if insights.get("views") is not None else None
                reach = int(insights["reach"]) if insights.get("reach") is not None else None
                saves = int(insights["saved"]) if insights.get("saved") is not None else None
                shares = int(insights["shares"]) if insights.get("shares") is not None else None
                impressions = int(insights["impressions"]) if insights.get("impressions") is not None else None
                total_interactions = int(insights["total_interactions"]) if insights.get("total_interactions") is not None else None
                likes = int(media_meta["like_count"]) if media_meta.get("like_count") is not None else None
                comments = int(media_meta["comments_count"]) if media_meta.get("comments_count") is not None else None

                avg_watch_raw = (
                    insights.get("avg_watch_time")
                    if insights.get("avg_watch_time") is not None
                    else insights.get("ig_reels_avg_watch_time")
                )
                avg_watch = float(avg_watch_raw) if avg_watch_raw is not None else None
                total_watch_raw = (
                    insights.get("total_watch_time")
                    if insights.get("total_watch_time") is not None
                    else insights.get("ig_reels_video_view_total_time")
                )
                total_watch = float(total_watch_raw) if total_watch_raw is not None else None
                follows = int(insights["follows"]) if insights.get("follows") is not None else None
                timestamped_retention_available = bool(insights.get("retention_curve"))
                source_type = "META_GRAPH_API"
            else:
                # Sandbox Simulation: visibly labeled simulated demo metrics matching catalog item
                views = int(media_meta["views"]) if media_meta.get("views") is not None else 28450
                likes = int(media_meta["likes"]) if media_meta.get("likes") is not None else 1840
                comments = int(media_meta["comments"]) if media_meta.get("comments") is not None else 162
                reach = int(round(views * 0.78))
                impressions = int(round(views * 1.10))
                shares = int(round(likes * 0.22))
                saves = int(round(likes * 0.45))
                avg_watch = None
                total_watch = None
                follows = None
                timestamped_retention_available = False
                source_type = "SANDBOX_SIMULATION"
        else:
            # Public URL / Pre-publish Upload: use ONLY explicitly user-supplied inputs; never invent defaults
            dec = declared_metrics or {}
            views = dec.get("declared_views")
            likes = dec.get("declared_likes")
            comments = dec.get("declared_comments")
            shares = dec.get("declared_shares")
            saves = dec.get("declared_saves")
            has_user_declared = any(v is not None for v in (views, likes, comments, shares, saves))
            source_type = "USER_DECLARED" if has_user_declared else "UNAVAILABLE"

        perf_metrics = calculate_reel_performance_metrics(
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            saves=saves,
            reach=reach,
            impressions=impressions,
            avg_watch_time=avg_watch,
            total_watch_time=total_watch,
            follows_attributed=follows,
            video_duration_seconds=duration,
            historical_avg_views=hist_avg_views,
            source_type=source_type,
            total_interactions=total_interactions,
            timestamped_retention_available=timestamped_retention_available,
        )

        non_null_core = sum(
            1 for k in ("views", "reach", "likes", "comments", "shares", "saves", "watch_ratio")
            if perf_metrics.get(k, {}).get("value") is not None
        )
        completeness = round(non_null_core / 7.0, 2)
        limitation_note = (
            "Sandbox simulated demo metrics — not live Instagram data."
            if is_sandbox_account
            else (
                "Private metrics unavailable without authenticated Meta Insights returning those fields."
                if job.analysis_mode != "CONNECTED_ACCOUNT" or non_null_core < 7
                else None
            )
        )

        # Record Metric Snapshot
        snapshot = ReelMetricSnapshot(
            workspace_id=job.workspace_id,
            job_id=job.id,
            views_count=views if views is not None else 0,
            reach_count=reach if reach is not None else 0,
            impressions_count=impressions if impressions is not None else 0,
            likes_count=likes if likes is not None else 0,
            comments_count=comments if comments is not None else 0,
            shares_count=shares if shares is not None else 0,
            saves_count=saves if saves is not None else 0,
            avg_watch_time_seconds=avg_watch,
            total_watch_time_seconds=total_watch,
            follows_attributed=follows,
            source_type=source_type,
            data_completeness=completeness,
            limitations_notes=limitation_note,
        )
        db.add(snapshot)
        db.commit()

        # Stage 4: AI Diagnosis & Scoring (90%)
        job.status = "GENERATING_AI_REPORT"
        job.progress_percent = 90
        job.stage_message = "Generating grounded diagnosis, timeline findings, and Reel-specific recommendations"
        db.commit()

        ai_report_data = generate_ai_diagnosis_report(
            video_intel=video_intel,
            performance_metrics=perf_metrics,
            caption=real_caption,
            title=real_title,
            analysis_mode=job.analysis_mode,
            video_filename=original_filename,
            timestamped_retention_available=timestamped_retention_available,
        )

        # Stage 5: Finalize & Persist Report Atomically (100%)
        scores = ai_report_data["scores"]
        saved_thumb = video_intel.get("hook_analysis", {}).get("first_frame_thumbnail_saved")
        if saved_thumb:
            thumbnail_url: Optional[str] = f"/api/v1/reel-intelligence/thumbnails/{saved_thumb}"
        elif authoritative_thumb_url:
            thumbnail_url = authoritative_thumb_url
        else:
            # Never substitute generic stock photography for an analyzed Reel
            thumbnail_url = None

        report_fields = {
            "title": real_title,
            "caption": real_caption,
            "analysis_mode": job.analysis_mode,
            "thumbnail_url": thumbnail_url,
            "duration_seconds": float(duration) if duration is not None else 0.0,
            "creative_quality_score": scores["creative_quality"]["score"],
            "performance_score": scores["performance"]["score"],
            "growth_conversion_score": scores["growth_conversion"]["score"],
            "viral_potential_estimate": scores["viral_potential"]["score"],
            "score_breakdown_json": json.dumps(scores),
            "calculated_metrics_json": json.dumps(perf_metrics),
            "video_intelligence_json": json.dumps(video_intel),
            "timeline_findings_json": json.dumps(ai_report_data["timeline_findings"]),
            "prioritized_action_plan_json": json.dumps(ai_report_data["prioritized_action_plan"]),
            "creative_alternatives_json": json.dumps(ai_report_data["creative_alternatives"]),
            "provenance_json": json.dumps(ai_report_data["provenance"]),
        }
        return upsert_reel_report_for_job(
            db=db,
            job=job,
            report_fields=report_fields,
            workspace_id=job.workspace_id,
        )

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception(
            "Reel analysis pipeline failed (job_id=%s, workspace_id=%s)",
            job_id,
            workspace_id or getattr(job, "workspace_id", None),
        )
        try:
            failed_job = db.query(ReelAnalysisJob).filter(ReelAnalysisJob.id == job_id).first()
            if failed_job:
                # Never downgrade an already-completed job with an existing report on secondary worker error
                if failed_job.status == "COMPLETED" and failed_job.report_id:
                    logger.warning(
                        "Preserving COMPLETED status for job_id=%s after sibling/secondary failure",
                        job_id,
                    )
                else:
                    failed_job.status = "FAILED"
                    failed_job.stage_message = "Analysis failed"
                    failed_job.error_message = sanitize_job_error_message(e)
                    db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            logger.exception("Failed to update FAILED state for job_id=%s", job_id)


def get_job_by_id(db: Session, job_id: str, workspace_id: str) -> Optional[ReelAnalysisJob]:
    return db.query(ReelAnalysisJob).filter(
        ReelAnalysisJob.id == job_id,
        ReelAnalysisJob.workspace_id == workspace_id
    ).first()


def get_report_by_id(db: Session, report_id: str, workspace_id: str) -> Optional[ReelReport]:
    return db.query(ReelReport).filter(
        ReelReport.id == report_id,
        ReelReport.workspace_id == workspace_id
    ).first()


def list_reports(
    db: Session,
    workspace_id: str,
    search: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[ReelReport]:
    query = db.query(ReelReport).filter(ReelReport.workspace_id == workspace_id)
    if search:
        query = query.filter(ReelReport.title.ilike(f"%{search}%"))
    if mode:
        query = query.filter(ReelReport.analysis_mode == mode)
    return query.order_by(ReelReport.created_at.desc()).offset(offset).limit(limit).all()


def compare_reels(db: Session, workspace_id: str, report_ids: List[str]) -> Dict[str, Any]:
    """Compares 2 to 5 reports, computing deltas, strengths, and AI synthesis."""
    if len(report_ids) < 2 or len(report_ids) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison requires between 2 and 5 report IDs."
        )

    if len(set(report_ids)) != len(report_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate report IDs provided for comparison."
        )

    reports = db.query(ReelReport).filter(
        ReelReport.id.in_(report_ids),
        ReelReport.workspace_id == workspace_id
    ).all()

    found_ids = {r.id for r in reports}
    missing_ids = [rid for rid in report_ids if rid not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report(s) not found in your workspace: {', '.join(missing_ids)}"
        )

    if len(reports) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 valid reports belonging to your workspace are required for comparison."
        )

    # Determine winner dynamically from valid available composite scores
    def _composite_score(rep: ReelReport) -> float:
        return float(rep.creative_quality_score + rep.performance_score + rep.growth_conversion_score)

    winner = max(reports, key=_composite_score)

    comparative_takeaways: List[str] = []
    winner_scores = json.loads(winner.score_breakdown_json) if winner.score_breakdown_json else {}
    winner_metrics = json.loads(winner.calculated_metrics_json) if winner.calculated_metrics_json else {}
    winner_prov = json.loads(winner.provenance_json) if winner.provenance_json else {}

    comparative_takeaways.append(
        f"'{winner.title}' led this comparison with Creative Quality {winner.creative_quality_score:.1f}/100 and Performance {winner.performance_score:.1f}/100."
    )

    er_entries = []
    has_simulated = False
    for r in reports:
        m = json.loads(r.calculated_metrics_json) if r.calculated_metrics_json else {}
        p = json.loads(r.provenance_json) if r.provenance_json else {}
        if p.get("is_simulated"):
            has_simulated = True
        er_val = m.get("engagement_rate", {}).get("value")
        if er_val is not None:
            er_entries.append((r.title, float(er_val), m.get("engagement_rate", {}).get("formatted", "")))

    if len(er_entries) >= 2:
        best_er = max(er_entries, key=lambda x: x[1])
        comparative_takeaways.append(
            f"Highest measured/reported engagement rate: '{best_er[0]}' at {best_er[2]}."
        )
    else:
        comparative_takeaways.append(
            "One or more compared Reels lack verified engagement rate data; score rankings rely heavily on visual/caption evaluations where metrics were unavailable."
        )

    measured_durations = [
        (r.title, r.duration_seconds)
        for r in reports
        if (json.loads(r.provenance_json) if r.provenance_json else {}).get("duration_measured")
    ]
    if len(measured_durations) >= 2:
        shortest = min(measured_durations, key=lambda x: x[1])
        comparative_takeaways.append(
            f"Decoded video durations range from {shortest[1]:.1f}s ('{shortest[0]}') up to {max(measured_durations, key=lambda x: x[1])[1]:.1f}s."
        )

    if has_simulated:
        comparative_takeaways.append(
            "Notice: At least one compared report contains Sandbox Simulated demo metrics rather than live Instagram insights."
        )

    return {
        "reports": reports,
        "winner_id": winner.id,
        "comparative_takeaways": comparative_takeaways
    }

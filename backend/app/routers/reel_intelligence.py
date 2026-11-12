import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Workspace
from app.models.reel_intelligence import ReelAnalysisJob, ReelReport, ReelComparison
from app.models.instagram import InstagramAccount
from app.schemas.reel_intelligence import (
    AnalyzePublicUrlRequest,
    AnalyzeConnectedReelRequest,
    ReelAnalysisJobResponse,
    ReelReportResponse,
    ReelReportSummary,
    ReelComparisonRequest,
    ReelComparisonResponse
)
from app.security import get_active_workspace, rate_limit, create_thumbnail_signature_token, verify_thumbnail_signature_token, resolve_workspace_from_authorization_header
from app.services.instagram_service import get_sandbox_media_catalog
from app.services.reel_intelligence_service import (
    create_or_get_url_analysis_job,
    create_upload_analysis_job,
    create_or_get_connected_reel_analysis_job,
    should_schedule_analysis_job,
    execute_reel_analysis,
    get_job_by_id,
    get_report_by_id,
    list_reports,
    compare_reels,
    resolve_authorized_thumbnail_path
)

router = APIRouter(prefix="/reel-intelligence", tags=["Woka Reel Intelligence"])


def sign_report_thumbnail_url(workspace_id: str, thumbnail_url: Optional[str]) -> Optional[str]:
    """Attaches a short-lived signed access token to workspace-local thumbnail URLs."""
    prefix = "/api/v1/reel-intelligence/thumbnails/"
    if thumbnail_url and thumbnail_url.startswith(prefix):
        filename = thumbnail_url[len(prefix):].split("?", 1)[0]
        if filename:
            token = create_thumbnail_signature_token(workspace_id, filename, expires_seconds=300)
            return f"{prefix}{filename}?token={token}"
    return thumbnail_url


def format_report_response(report: ReelReport) -> ReelReportResponse:
    """Helper to deserialize stored JSON columns into typed schema."""
    scores_dict = json.loads(report.score_breakdown_json) if report.score_breakdown_json else {}
    metrics_dict = json.loads(report.calculated_metrics_json) if report.calculated_metrics_json else {}
    video_intel_dict = json.loads(report.video_intelligence_json) if report.video_intelligence_json else {}
    timeline_list = json.loads(report.timeline_findings_json) if report.timeline_findings_json else []
    action_plan_list = json.loads(report.prioritized_action_plan_json) if report.prioritized_action_plan_json else []
    creative_alt_dict = json.loads(report.creative_alternatives_json) if report.creative_alternatives_json else {}
    provenance_dict = json.loads(report.provenance_json) if report.provenance_json else {}

    return ReelReportResponse(
        id=report.id,
        workspace_id=report.workspace_id,
        job_id=report.job_id,
        title=report.title,
        caption=report.caption,
        analysis_mode=report.analysis_mode,
        thumbnail_url=sign_report_thumbnail_url(report.workspace_id, report.thumbnail_url),
        duration_seconds=report.duration_seconds,
        scores=scores_dict,
        calculated_metrics=metrics_dict,
        video_intelligence=video_intel_dict,
        timeline_findings=timeline_list,
        prioritized_action_plan=action_plan_list,
        creative_alternatives=creative_alt_dict,
        provenance=provenance_dict,
        created_at=report.created_at,
        updated_at=report.updated_at
    )


@router.post("/jobs/url", response_model=ReelAnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze_public_url(
    req: AnalyzePublicUrlRequest,
    background_tasks: BackgroundTasks,
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db),
    _limiter: bool = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    """
    Submits a public Instagram Reel or video URL for end-to-end AI analysis.
    Executes asynchronously with real-time status polling.
    """

    declared_dict = {
        "declared_views": req.declared_views,
        "declared_likes": req.declared_likes,
        "declared_comments": req.declared_comments,
        "declared_shares": req.declared_shares,
        "declared_saves": req.declared_saves
    }
    
    job, created = create_or_get_url_analysis_job(db, workspace.id, req.url, declared_dict)
    # Reuse existing report/execution when an idempotent completed or active job is returned
    if should_schedule_analysis_job(db, job, created):
        background_tasks.add_task(execute_reel_analysis, db, job.id, declared_dict, workspace.id)
    return job


@router.post("/jobs/upload", response_model=ReelAnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze_video_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db),
    _limiter: bool = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    """
    Uploads a video file (.mp4, .mov, .webm) and triggers full video intelligence analysis.
    """

    job = create_upload_analysis_job(db, workspace.id, file)
    background_tasks.add_task(execute_reel_analysis, db, job.id, None, workspace.id)
    return job


@router.post("/jobs/connected", response_model=ReelAnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze_connected_reel(
    req: AnalyzeConnectedReelRequest,
    background_tasks: BackgroundTasks,
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db),
    _limiter: bool = Depends(rate_limit(max_requests=20, window_seconds=60))
):
    """
    Submits a Reel from the creator's connected Instagram professional account.
    Retrieves official Meta Graph API insights (reach, saves, completion ratio).
    """

    job, created = create_or_get_connected_reel_analysis_job(
        db,
        workspace_id=workspace.id,
        media_id=req.media_id,
        title=req.title,
        caption=req.caption,
        media_url=req.media_url,
        thumbnail_url=req.thumbnail_url
    )
    if should_schedule_analysis_job(db, job, created):
        cached_media = getattr(job, "_authoritative_media_cache", None)
        background_tasks.add_task(execute_reel_analysis, db, job.id, None, workspace.id, cached_media)
    return job


@router.get("/jobs/{job_id}", response_model=ReelAnalysisJobResponse)
def get_job_status(
    job_id: str,
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db)
):
    """Polls real-time progress and status of an analysis job."""

    job = get_job_by_id(db, job_id, workspace.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis job not found or does not belong to your workspace."
        )
    return job


@router.get("/reports/{report_id}", response_model=ReelReportResponse)
def get_report(
    report_id: str,
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db)
):
    """Retrieves the complete Reel Intelligence report."""

    report = get_report_by_id(db, report_id, workspace.id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reel report not found."
        )
    return format_report_response(report)


@router.get("/reports", response_model=List[ReelReportSummary])
def get_report_history(
    search: Optional[str] = None,
    mode: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db)
):
    """Lists past Reel reports for the workspace."""

    reports = list_reports(db, workspace.id, search=search, mode=mode, limit=limit, offset=offset)
    
    summaries = []
    for r in reports:
        metrics = json.loads(r.calculated_metrics_json) if r.calculated_metrics_json else {}
        provenance = json.loads(r.provenance_json) if r.provenance_json else {}
        views_raw = metrics.get("views", {}).get("value")
        likes_raw = metrics.get("likes", {}).get("value")
        er_raw = metrics.get("engagement_rate", {}).get("value")
        views_val = int(views_raw) if views_raw is not None else None
        likes_val = int(likes_raw) if likes_raw is not None else None
        er_val = float(er_raw) if er_raw is not None else None

        summaries.append(ReelReportSummary(
            id=r.id,
            workspace_id=r.workspace_id,
            job_id=r.job_id,
            title=r.title,
            analysis_mode=r.analysis_mode,
            thumbnail_url=sign_report_thumbnail_url(r.workspace_id, r.thumbnail_url),
            duration_seconds=r.duration_seconds,
            duration_measured=bool(provenance.get("duration_measured", r.duration_seconds > 0)),
            is_simulated=bool(provenance.get("is_simulated", False)),
            metric_source=provenance.get("metric_source_mode"),
            creative_quality_score=r.creative_quality_score,
            performance_score=r.performance_score,
            growth_conversion_score=r.growth_conversion_score,
            viral_potential_estimate=r.viral_potential_estimate,
            views_count=views_val,
            likes_count=likes_val,
            engagement_rate=er_val,
            created_at=r.created_at
        ))
    return summaries


@router.post("/compare", response_model=ReelComparisonResponse)
def compare_reports(
    req: ReelComparisonRequest,
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db)
):
    """Compares 2 to 5 Reel reports side-by-side."""

    comp_result = compare_reels(db, workspace.id, req.report_ids)
    
    formatted_reports = [format_report_response(r) for r in comp_result["reports"]]
    
    # Save comparison record
    comp_record = ReelComparison(
        workspace_id=workspace.id,
        report_ids=json.dumps(req.report_ids),
        comparison_summary_json=json.dumps({
            "winner_id": comp_result["winner_id"],
            "comparative_takeaways": comp_result["comparative_takeaways"]
        })
    )
    db.add(comp_record)
    db.commit()
    db.refresh(comp_record)

    return ReelComparisonResponse(
        id=comp_record.id,
        workspace_id=workspace.id,
        report_ids=req.report_ids,
        reports=formatted_reports,
        comparison_matrix={
            "total_compared": len(formatted_reports),
            "winner_title": next((r.title for r in formatted_reports if r.id == comp_result["winner_id"]), "")
        },
        comparative_takeaways=comp_result["comparative_takeaways"],
        winner_id=comp_result["winner_id"],
        created_at=comp_record.created_at
    )


@router.post("/jobs/{job_id}/retry", response_model=ReelAnalysisJobResponse)
def retry_failed_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db)
):
    """Retries an eligible failed analysis job."""

    job = get_job_by_id(db, job_id, workspace.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found."
        )
    if job.status not in ["FAILED", "QUEUED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry a job with status '{job.status}'."
        )

    job.status = "QUEUED"
    job.progress_percent = 5
    job.stage_message = "Retrying analysis"
    job.error_message = None
    db.commit()
    db.refresh(job)

    background_tasks.add_task(execute_reel_analysis, db, job.id, None, workspace.id)
    return job


@router.get("/connected-reels")
def list_connected_account_reels(
    workspace: Workspace = Depends(get_active_workspace),
    db: Session = Depends(get_db)
):
    """
    Returns candidate Reels from the creator's connected Instagram professional account
    ready for 1-click analysis.
    """

    account = db.query(InstagramAccount).filter(
        InstagramAccount.workspace_id == workspace.id,
        InstagramAccount.is_connected == True
    ).first()

    if not account:
        return {
            "has_connected_account": False,
            "message": "Connect your Instagram Professional Account to analyze published Reels.",
            "reels": []
        }

    if not account.is_sandbox:
        from app.services.instagram_service import fetch_instagram_media_list, MetaTokenExpiredError
        from app.security import decrypt_token
        plain_token = decrypt_token(account.encrypted_access_token)
        if not plain_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Instagram access token is missing or corrupted. Please reconnect."
            )
        try:
            from app.models.reel_intelligence import ReelMetricSnapshot, ReelAnalysisJob
            items = fetch_instagram_media_list(plain_token, user_id=account.ig_user_id, limit=25)
            live_reels = []
            for item in items:
                m_type = item.get("media_type")
                p_type = item.get("media_product_type")
                m_id = item.get("id")
                # Look up actual verified snapshot if previously synchronized
                recent_snapshot = db.query(ReelMetricSnapshot).filter(
                    ReelMetricSnapshot.workspace_id == workspace.id
                ).join(ReelAnalysisJob, ReelAnalysisJob.id == ReelMetricSnapshot.job_id).filter(
                    ReelAnalysisJob.source_media_id == m_id
                ).order_by(ReelMetricSnapshot.snapshot_timestamp.desc()).first()

                actual_views = recent_snapshot.views_count if recent_snapshot else None

                if m_type == "VIDEO" or p_type == "REELS":
                    live_reels.append({
                        "media_id": m_id,
                        "title": (item.get("caption") or "Instagram Reel").split("\n")[0][:60],
                        "caption": item.get("caption") or "",
                        "thumbnail_url": item.get("thumbnail_url") or "",
                        "media_url": item.get("media_url") or "",
                        "permalink": item.get("permalink") or "",
                        "views": actual_views if actual_views is not None else 0,
                        "views_available": actual_views is not None,
                        "likes": int(item["like_count"]) if item.get("like_count") is not None else 0,
                        "likes_available": item.get("like_count") is not None,
                        "comments": int(item["comments_count"]) if item.get("comments_count") is not None else 0,
                        "comments_available": item.get("comments_count") is not None,
                        "published_at": item.get("timestamp") or "",
                        "has_synced_insights": actual_views is not None,
                        "is_simulated": False,
                        "data_source": "META_GRAPH_API",
                    })
            return {
                "has_connected_account": True,
                "username": account.username,
                "is_sandbox": False,
                "reels": live_reels
            }
        except MetaTokenExpiredError as e:
            account.is_connected = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Instagram access token expired or revoked: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Meta Graph API error retrieving reels: {str(e)}"
            )

    # Sample connected account Reels for sandbox demo mode (explicitly labeled simulated)
    sandbox_catalog = get_sandbox_media_catalog(account.ig_user_id)[:3]
    sample_reels = [
        {
            "media_id": item["id"],
            "title": item["title"],
            "caption": item["caption"],
            "thumbnail_url": item.get("thumbnail_url") or "",
            "media_url": item.get("media_url") or "",
            "permalink": item.get("permalink") or "",
            "views": item.get("views", 0),
            "likes": item.get("likes", 0),
            "comments": item.get("comments", 0),
            "published_at": item.get("timestamp") or "",
            "is_simulated": True,
            "data_source": "SANDBOX_SIMULATION",
            "has_synced_insights": False,
        }
        for item in sandbox_catalog
    ]

    return {
        "has_connected_account": True,
        "username": account.username,
        "is_sandbox": True,
        "reels": sample_reels
    }


@router.get("/thumbnails/{filename:path}")
def serve_thumbnail(
    filename: str,
    token: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_workspace_id: Optional[str] = Header(default=None, alias="X-Workspace-Id"),
    db: Session = Depends(get_db),
):
    """Serves locally generated video frame thumbnails exclusively to authorized workspace members."""
    if authorization:
        workspace = resolve_workspace_from_authorization_header(
            db=db,
            authorization=authorization,
            x_workspace_id=x_workspace_id,
        )
        authorized_workspace_id = workspace.id
    elif token:
        authorized_workspace_id = verify_thumbnail_signature_token(token, filename)
        if not authorized_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired thumbnail access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access workspace thumbnails.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    file_path = resolve_authorized_thumbnail_path(authorized_workspace_id, filename)
    return FileResponse(
        file_path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )

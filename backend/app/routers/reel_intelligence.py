import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
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
from app.security import get_current_user
from app.services.auth_service import get_or_create_workspace
from app.services.reel_intelligence_service import (
    create_url_analysis_job,
    create_upload_analysis_job,
    create_connected_reel_analysis_job,
    execute_reel_analysis,
    get_job_by_id,
    get_report_by_id,
    list_reports,
    compare_reels
)

router = APIRouter(prefix="/reel-intelligence", tags=["Woka Reel Intelligence"])


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
        thumbnail_url=report.thumbnail_url,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits a public Instagram Reel or video URL for end-to-end AI analysis.
    Executes asynchronously with real-time status polling.
    """
    workspace = get_or_create_workspace(db, current_user)
    declared_dict = {
        "declared_views": req.declared_views,
        "declared_likes": req.declared_likes,
        "declared_comments": req.declared_comments,
        "declared_shares": req.declared_shares,
        "declared_saves": req.declared_saves
    }
    
    job = create_url_analysis_job(db, workspace.id, req.url, declared_dict)
    # Execute immediately in background task for high responsiveness
    background_tasks.add_task(execute_reel_analysis, db, job.id, declared_dict)
    return job


@router.post("/jobs/upload", response_model=ReelAnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze_video_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a video file (.mp4, .mov, .webm) and triggers full video intelligence analysis.
    """
    workspace = get_or_create_workspace(db, current_user)
    job = create_upload_analysis_job(db, workspace.id, file)
    background_tasks.add_task(execute_reel_analysis, db, job.id)
    return job


@router.post("/jobs/connected", response_model=ReelAnalysisJobResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze_connected_reel(
    req: AnalyzeConnectedReelRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits a Reel from the creator's connected Instagram professional account.
    Retrieves official Meta Graph API insights (reach, saves, completion ratio).
    """
    workspace = get_or_create_workspace(db, current_user)
    job = create_connected_reel_analysis_job(
        db,
        workspace_id=workspace.id,
        media_id=req.media_id,
        title=req.title,
        caption=req.caption,
        media_url=req.media_url,
        thumbnail_url=req.thumbnail_url
    )
    background_tasks.add_task(execute_reel_analysis, db, job.id)
    return job


@router.get("/jobs/{job_id}", response_model=ReelAnalysisJobResponse)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Polls real-time progress and status of an analysis job."""
    workspace = get_or_create_workspace(db, current_user)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the complete Reel Intelligence report."""
    workspace = get_or_create_workspace(db, current_user)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists past Reel reports for the workspace."""
    workspace = get_or_create_workspace(db, current_user)
    reports = list_reports(db, workspace.id, search=search, mode=mode, limit=limit, offset=offset)
    
    summaries = []
    for r in reports:
        metrics = json.loads(r.calculated_metrics_json) if r.calculated_metrics_json else {}
        views_val = int(metrics.get("views", {}).get("value", 0)) if metrics.get("views", {}).get("value") else 0
        likes_val = int(metrics.get("likes", {}).get("value", 0)) if metrics.get("likes", {}).get("value") else 0
        er_val = float(metrics.get("engagement_rate", {}).get("value", 0.0)) if metrics.get("engagement_rate", {}).get("value") else 0.0
        
        summaries.append(ReelReportSummary(
            id=r.id,
            workspace_id=r.workspace_id,
            job_id=r.job_id,
            title=r.title,
            analysis_mode=r.analysis_mode,
            thumbnail_url=r.thumbnail_url,
            duration_seconds=r.duration_seconds,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compares 2 to 5 Reel reports side-by-side."""
    workspace = get_or_create_workspace(db, current_user)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retries an eligible failed analysis job."""
    workspace = get_or_create_workspace(db, current_user)
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

    background_tasks.add_task(execute_reel_analysis, db, job.id)
    return job


@router.get("/connected-reels")
def list_connected_account_reels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns candidate Reels from the creator's connected Instagram professional account
    ready for 1-click analysis.
    """
    workspace = get_or_create_workspace(db, current_user)
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
        from app.services.instagram_service import fetch_instagram_media_list
        from app.security import decrypt_token
        plain_token = decrypt_token(account.encrypted_access_token)
        if not plain_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Instagram access token is missing or corrupted. Please reconnect."
            )
        try:
            items = fetch_instagram_media_list(plain_token, limit=25)
            live_reels = []
            for item in items:
                m_type = item.get("media_type")
                p_type = item.get("media_product_type")
                if m_type == "VIDEO" or p_type == "REELS":
                    live_reels.append({
                        "media_id": item.get("id"),
                        "title": (item.get("caption") or "Instagram Reel").split("\n")[0][:60],
                        "caption": item.get("caption") or "",
                        "thumbnail_url": item.get("thumbnail_url") or item.get("media_url") or "",
                        "media_url": item.get("media_url") or "",
                        "views": int(item.get("like_count", 0) * 10),
                        "likes": int(item.get("like_count", 0)),
                        "comments": int(item.get("comments_count", 0)),
                        "published_at": item.get("timestamp") or ""
                    })
            return {
                "has_connected_account": True,
                "username": account.username,
                "is_sandbox": False,
                "reels": live_reels
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Meta Graph API error retrieving reels: {str(e)}"
            )

    # Sample connected account Reels for immediate 1-click analysis (sandbox mode)
    sample_reels = [
        {
            "media_id": f"ig_reel_{account.ig_user_id}_101",
            "title": "3 Hook Mistakes That Kill Your Retention",
            "caption": "Stop starting your Reels with a generic 3-second logo intro. Here's what to do instead. Comment REEL for the checklist! 👇",
            "thumbnail_url": "https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?w=600&auto=format&fit=crop&q=80",
            "media_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "views": 48200,
            "likes": 3120,
            "comments": 240,
            "published_at": "2026-10-12T14:30:00Z"
        },
        {
            "media_id": f"ig_reel_{account.ig_user_id}_102",
            "title": "The 140 WPM Sweet Spot for Spoken Pacing",
            "caption": "Why rapid-fire delivery without pauses keeps viewers watching until the very end. Save this before recording!",
            "thumbnail_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=600&auto=format&fit=crop&q=80",
            "media_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
            "views": 22100,
            "likes": 1420,
            "comments": 88,
            "published_at": "2026-10-08T09:15:00Z"
        },
        {
            "media_id": f"ig_reel_{account.ig_user_id}_103",
            "title": "Safe Zones: Don't Let Instagram Hide Your Subtitles",
            "caption": "If your captions sit in the bottom 20%, half your audience can't read them. Here is the certified safe template.",
            "thumbnail_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80",
            "media_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
            "views": 16900,
            "likes": 980,
            "comments": 64,
            "published_at": "2026-10-02T18:45:00Z"
        }
    ]

    return {
        "has_connected_account": True,
        "username": account.username,
        "is_sandbox": True,
        "reels": sample_reels
    }


@router.get("/thumbnails/{filename}")
def serve_thumbnail(filename: str):
    """Serves locally generated video frame thumbnails securely."""
    # Prevent directory traversal
    clean_filename = os.path.basename(filename)
    # Search across media storage subfolders
    for root, _, files in os.walk(os.path.join(os.getcwd(), "media_storage")):
        if clean_filename in files:
            file_path = os.path.join(root, clean_filename)
            return FileResponse(file_path, media_type="image/jpeg")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found.")

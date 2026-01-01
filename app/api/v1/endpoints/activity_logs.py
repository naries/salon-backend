from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.models import ActivityLog, User, Salon
from app.core.security import get_current_user, get_current_superadmin
from pydantic import BaseModel
import json

router = APIRouter()


# Schemas
class ActivityLogCreate(BaseModel):
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None

class ActivityLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    salon_id: Optional[int] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[str] = None
    created_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    salon_name: Optional[str] = None

    class Config:
        from_attributes = True


def create_activity_log(
    db: Session,
    user_id: int,
    salon_id: int,
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    description: str = None,
    ip_address: str = None,
    user_agent: str = None,
    metadata: dict = None
):
    """Helper function to create activity log"""
    log = ActivityLog(
        user_id=user_id,
        salon_id=salon_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=json.dumps(metadata) if metadata else None
    )
    db.add(log)
    db.commit()
    return log


@router.get("/", response_model=List[ActivityLogResponse])
def get_activity_logs(
    skip: int = 0,
    limit: int = 100,
    action: str = None,
    entity_type: str = None,
    salon_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get all activity logs (superadmin only)"""
    query = db.query(ActivityLog).order_by(ActivityLog.created_at.desc())
    
    if action:
        query = query.filter(ActivityLog.action == action)
    
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    
    if salon_id:
        query = query.filter(ActivityLog.salon_id == salon_id)
    
    logs = query.offset(skip).limit(limit).all()
    
    # Enrich with user and salon info
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        salon = db.query(Salon).filter(Salon.id == log.salon_id).first() if log.salon_id else None
        
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "salon_id": log.salon_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "metadata": log.extra_data,
            "created_at": log.created_at,
            "user_email": user.email if user else None,
            "user_name": user.full_name if user else None,
            "salon_name": salon.name if salon else None,
        }
        result.append(log_dict)
    
    return result


@router.get("/my-salon", response_model=List[ActivityLogResponse])
def get_my_salon_activity_logs(
    skip: int = 0,
    limit: int = 50,
    action: str = None,
    entity_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get activity logs for the current user's salon"""
    if not current_user.salon_id:
        raise HTTPException(status_code=400, detail="User not associated with a salon")
    
    query = db.query(ActivityLog).filter(
        ActivityLog.salon_id == current_user.salon_id
    ).order_by(ActivityLog.created_at.desc())
    
    if action:
        query = query.filter(ActivityLog.action == action)
    
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    
    logs = query.offset(skip).limit(limit).all()
    
    # Enrich with user info
    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
        
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "salon_id": log.salon_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "metadata": log.extra_data,
            "created_at": log.created_at,
            "user_email": user.email if user else None,
            "user_name": user.full_name if user else None,
            "salon_name": None,  # Not needed for own salon
        }
        result.append(log_dict)
    
    return result


@router.post("/", response_model=ActivityLogResponse)
def create_log(
    log_data: ActivityLogCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an activity log entry"""
    log = create_activity_log(
        db=db,
        user_id=current_user.id,
        salon_id=current_user.salon_id,
        action=log_data.action,
        entity_type=log_data.entity_type,
        entity_id=log_data.entity_id,
        description=log_data.description,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata=log_data.metadata
    )
    
    user = db.query(User).filter(User.id == log.user_id).first()
    salon = db.query(Salon).filter(Salon.id == log.salon_id).first() if log.salon_id else None
    
    return {
        **log.__dict__,
        "user_email": user.email if user else None,
        "user_name": user.full_name if user else None,
        "salon_name": salon.name if salon else None,
    }


@router.get("/stats")
def get_activity_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """Get activity statistics (superadmin only)"""
    from sqlalchemy import func
    
    # Total logs
    total_logs = db.query(func.count(ActivityLog.id)).scalar()
    
    # Logs by action
    logs_by_action = db.query(
        ActivityLog.action,
        func.count(ActivityLog.id).label('count')
    ).group_by(ActivityLog.action).all()
    
    # Logs by entity type
    logs_by_entity = db.query(
        ActivityLog.entity_type,
        func.count(ActivityLog.id).label('count')
    ).group_by(ActivityLog.entity_type).all()
    
    # Recent activity (last 7 days)
    from datetime import timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_logs = db.query(func.count(ActivityLog.id)).filter(
        ActivityLog.created_at >= seven_days_ago
    ).scalar()
    
    return {
        "total_logs": total_logs,
        "recent_logs_7_days": recent_logs,
        "by_action": [{"action": action, "count": count} for action, count in logs_by_action],
        "by_entity_type": [{"entity_type": entity_type, "count": count} for entity_type, count in logs_by_entity if entity_type],
    }

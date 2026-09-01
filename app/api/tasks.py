import json
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User
from app.models.credential import SinicaCredential
from app.models.booking_task import BookingTask
from app.services.auth_service import get_current_user
from app.services.sniper_bridge import SniperBridge

router = APIRouter(prefix="/api/tasks", tags=["搶票任務管理"])

class CreateTaskRequest(BaseModel):
    target_date: str # 例如 "09/06"
    target_day_num: str # 例如 "06"
    primary_slots: List[str] # 例如 ["17:00", "18:00"]
    court_order: Optional[List[str]] = ["A", "B"]
    enable_fallback: bool = True
    fallback_min_hour: int = 14
    fallback_max_hour: int = 17
    refresh_attempts: int = 40
    refresh_interval_ms: int = 300
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    target_date: str
    target_day_num: str
    primary_slots: List[str]
    court_order: List[str]
    enable_fallback: bool
    fallback_min_hour: int
    fallback_max_hour: int
    status: str
    result_message: Optional[str]
    screenshot_path: Optional[str]
    created_at: str

@router.get("/", response_model=List[TaskResponse])
def list_tasks(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    tasks = session.exec(
        select(BookingTask).where(BookingTask.user_id == user.id).order_by(BookingTask.created_at.desc())
    ).all()
    
    return [
        TaskResponse(
            id=t.id,
            target_date=t.target_date,
            target_day_num=t.target_day_num,
            primary_slots=t.primary_slots,
            court_order=t.court_order,
            enable_fallback=t.enable_fallback,
            fallback_min_hour=t.fallback_min_hour,
            fallback_max_hour=t.fallback_max_hour,
            status=t.status,
            result_message=t.result_message,
            screenshot_path=t.screenshot_path,
            created_at=t.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
        for t in tasks
    ]

@router.post("/create", response_model=TaskResponse)
def create_task(req: CreateTaskRequest, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    cred = session.exec(select(SinicaCredential).where(SinicaCredential.user_id == user.id)).first()
    if not cred or not cred.is_valid:
        raise HTTPException(status_code=400, detail="請先至「中研院憑證設定」填寫並驗證您的帳號密碼！")

    task = BookingTask(
        user_id=user.id,
        target_date=req.target_date,
        target_day_num=req.target_day_num,
        primary_slots_json=json.dumps(req.primary_slots),
        court_order_json=json.dumps(req.court_order),
        enable_fallback=req.enable_fallback,
        fallback_min_hour=req.fallback_min_hour,
        fallback_max_hour=req.fallback_max_hour,
        refresh_attempts=req.refresh_attempts,
        refresh_interval_ms=req.refresh_interval_ms,
        telegram_bot_token=req.telegram_bot_token,
        telegram_chat_id=req.telegram_chat_id,
        status="pending"
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    return TaskResponse(
        id=task.id,
        target_date=task.target_date,
        target_day_num=task.target_day_num,
        primary_slots=task.primary_slots,
        court_order=task.court_order,
        enable_fallback=task.enable_fallback,
        fallback_min_hour=task.fallback_min_hour,
        fallback_max_hour=task.fallback_max_hour,
        status=task.status,
        result_message=task.result_message,
        screenshot_path=task.screenshot_path,
        created_at=task.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )

@router.delete("/{task_id}")
def delete_task(task_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    task = session.get(BookingTask, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="找不到該任務")
    session.delete(task)
    session.commit()
    return {"success": True, "message": "任務已刪除"}

@router.post("/{task_id}/dry-run")
async def run_task_dry_run(
    task_id: int,
    seconds: int = 5,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    task = session.get(BookingTask, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="找不到該任務")
        
    cred = session.exec(select(SinicaCredential).where(SinicaCredential.user_id == user.id)).first()
    if not cred or not cred.state_file_path:
        raise HTTPException(status_code=400, detail="請先驗證中研院憑證以生成 Session 狀態")

    result = await SniperBridge.execute_task(task, cred.state_file_path, dry_run=True, dry_run_seconds=seconds)
    
    return {
        "success": result["success"],
        "message": "模擬推演執行完成！",
        "screenshot": result.get("screenshot")
    }

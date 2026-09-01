import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from sqlmodel import Session, select

from app.database import engine
from app.models.booking_task import BookingTask
from app.models.credential import SinicaCredential
from app.services.sniper_bridge import SniperBridge
from src.time_sync import get_now

class TaskScheduler:
    _instance = None

    def __init__(self):
        self.is_running = False
        self._bg_task = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TaskScheduler()
        return cls._instance

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._bg_task = asyncio.create_task(self._scheduler_loop())
            print("🚀 [SaaS Scheduler] 背景任務排程器已啟動")

    def stop(self):
        self.is_running = False
        if self._bg_task:
            self._bg_task.cancel()
            print("🛑 [SaaS Scheduler] 背景任務排程器已停止")

    async def _scheduler_loop(self):
        while self.is_running:
            try:
                await self._check_and_trigger_tasks()
            except Exception as e:
                print(f"⚠️ [SaaS Scheduler] 排程循環例外: {e}")
            await asyncio.sleep(10) # 每 10 秒檢查一次

    def resolve_conflicts(self, tasks: List[BookingTask]) -> List[BookingTask]:
        """
        智慧避讓演算法：
        多個任務選中同日期、同時段時，依據建立時間分流場地順序 (A場 vs B場)
        """
        allocated_slots: Dict[str, int] = {} # "MM/DD-Court-Slot" -> task_id
        
        for task in sorted(tasks, key=lambda t: t.created_at):
            court_order = task.court_order.copy()
            # 若第一志願在 A 場已被其他任務佔用，且 B 場可用，自動將 B 場優先級提升
            primary_slot = task.primary_slots[0] if task.primary_slots else "17:00"
            key_a = f"{task.target_date}-A-{primary_slot}"
            
            if key_a in allocated_slots and "B" in court_order:
                # 避讓分流至 B 場
                court_order = ["B", "A"]
                task.court_order_json = json.dumps(court_order)
            
            # 登記第一志願
            primary_court = court_order[0]
            allocated_slots[f"{task.target_date}-{primary_court}-{primary_slot}"] = task.id
            
        return tasks

    async def _check_and_trigger_tasks(self):
        now = get_now()
        target_tonight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now.hour >= 12:
            target_tonight += timedelta(days=1)

        diff_seconds = (target_tonight - now).total_seconds()
        
        # 僅在放票前 10 分鐘以內 (23:50 ~ 23:59) 觸發自動 Session 換發與預備
        with Session(engine) as db:
            pending_tasks = db.exec(
                select(BookingTask).where(BookingTask.status == "pending")
            ).all()

            if not pending_tasks:
                return

            # 如果距放票小於 10 分鐘 (600秒)，預熱準備
            if 0 < diff_seconds <= 600:
                print(f"⏰ [SaaS Scheduler] 進入放票前預備階段 (剩餘 {int(diff_seconds)} 秒)，執行避讓分配與 Session 預熱...")
                resolved_tasks = self.resolve_conflicts(list(pending_tasks))
                
                for task in resolved_tasks:
                    cred = db.exec(
                        select(SinicaCredential).where(SinicaCredential.user_id == task.user_id)
                    ).first()
                    
                    if not cred:
                        task.status = "failed"
                        task.result_message = "未設定中研院帳號密碼憑證"
                        db.add(task)
                        db.commit()
                        continue

                    # 自動換發 Session
                    ok, msg, state_path = await SniperBridge.auto_login_and_save_state(cred)
                    if ok:
                        task.status = "running"
                        db.add(task)
                        db.commit()
                        # 啟動獨立非同步 Worker 執行實戰搶票
                        asyncio.create_task(self._run_worker(task.id, state_path))
                    else:
                        task.status = "failed"
                        task.result_message = f"Session 預熱失敗: {msg}"
                        db.add(task)
                        db.commit()

    async def _run_worker(self, task_id: int, state_path: str):
        with Session(engine) as db:
            task = db.get(BookingTask, task_id)
            if not task:
                return
        
        result = await SniperBridge.execute_task(task, state_path, dry_run=False)
        
        with Session(engine) as db:
            task = db.get(BookingTask, task_id)
            if task:
                task.status = "success" if result["success"] else "failed"
                task.executed_at = datetime.utcnow()
                task.screenshot_path = result.get("screenshot")
                task.result_message = "預約成功！" if result["success"] else "本次衝刺未獲取到目標時段"
                db.add(task)
                db.commit()

scheduler = TaskScheduler.get_instance()

import json
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field

class BookingTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    
    # 目標日期 (例如 "09/05") 與日曆數字 (例如 "05")
    target_date: str = Field(index=True)
    target_day_num: str
    
    # 志願序時段 (以 JSON 陣列儲存，例如 '["17:00", "18:00"]')
    primary_slots_json: str = Field(default='["17:00", "18:00"]')
    
    # 場地優先順序 (例如 '["A", "B"]')
    court_order_json: str = Field(default='["A", "B"]')
    
    # 撿漏範圍 (14:00 <= 開始時間 < 17:00)
    enable_fallback: bool = Field(default=True)
    fallback_min_hour: int = Field(default=14)
    fallback_max_hour: int = Field(default=17)
    
    # 進階精密微調 (毫秒)
    refresh_attempts: int = Field(default=40)
    refresh_interval_ms: int = Field(default=300)
    time_offset_ms: int = Field(default=0) # 手動時間偏移補償
    
    # 通知整合
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    line_notify_token: Optional[str] = None
    
    # 任務狀態: pending (待執行), running (進行中), success (成功), failed (失敗), cancelled (已取消)
    status: str = Field(default="pending", index=True)
    result_message: Optional[str] = None
    booked_slots_json: Optional[str] = None # 預約成功時段清單
    screenshot_path: Optional[str] = None # 結果截圖路徑
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None

    @property
    def primary_slots(self) -> List[str]:
        try:
            return json.loads(self.primary_slots_json)
        except Exception:
            return ["17:00", "18:00"]

    @property
    def court_order(self) -> List[str]:
        try:
            return json.loads(self.court_order_json)
        except Exception:
            return ["A", "B"]

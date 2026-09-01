from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class SinicaCredential(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    account_encrypted: str # AES-256 加密身分證號 / 帳號
    password_encrypted: str # AES-256 加密密碼
    state_file_path: Optional[str] = None # 生成的 storage_state 路徑
    is_valid: bool = Field(default=False)
    last_verified_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

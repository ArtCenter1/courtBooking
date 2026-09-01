from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str = Field(default="")
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    quota: int = Field(default=10) # 可預約任務配額
    created_at: datetime = Field(default_factory=datetime.utcnow)

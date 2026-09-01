import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    PROJECT_NAME: str = "中研院網球場智慧預約 SaaS 平台"
    PROJECT_VERSION: str = "0.2.0-beta"
    
    # 伺服器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # 資料庫配置
    DB_DIR: Path = BASE_DIR / "data"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/court_booking.db"
    
    # 安全與金鑰
    SECRET_KEY: str = os.getenv("SAAS_SECRET_KEY", "sinica-tennis-court-super-secret-key-2026")
    ENCRYPTION_KEY: str = os.getenv("SAAS_ENCRYPTION_KEY", "sinica-vault-master-crypto-key-2026=") # 32-byte key
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 天免重複登入
    
    # 截圖與日誌目錄
    DATA_DIR: Path = BASE_DIR / "data"
    SCREENSHOT_DIR: Path = BASE_DIR / "data" / "screenshots"
    LOGS_DIR: Path = BASE_DIR / "data" / "logs"
    
    # 中研院系統 URL
    SINICA_GYM_URL: str = "https://gym.dga.sinica.edu.tw/reservation.html"

settings = Settings()

# 確保必要目錄存在
settings.DB_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

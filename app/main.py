from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import api_router
from app.services.scheduler import scheduler

STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時：初始化資料庫與背景排程器
    print("🌟 [SaaS Main] 初始化資料庫模型與安全金庫...")
    init_db()
    scheduler.start()
    yield
    # 關閉時：停止排程器
    scheduler.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 API 路由
app.include_router(api_router)

# 掛載靜態資源目錄
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 根路徑主頁
@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.PROJECT_VERSION}

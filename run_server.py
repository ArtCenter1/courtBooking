"""
中研院網球場智慧預約 SaaS 服務啟動器
"""
import sys
import uvicorn
from app.config import settings

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def main():
    print("==================================================")
    print(f"🚀 啟動 {settings.PROJECT_NAME} (v{settings.PROJECT_VERSION})")
    print(f"🌐 網頁介面位址: http://127.0.0.1:{settings.PORT}")
    print(f"📖 API 文件介面: http://127.0.0.1:{settings.PORT}/docs")
    print("==================================================")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)

if __name__ == "__main__":
    main()

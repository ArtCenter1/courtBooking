from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User
from app.models.credential import SinicaCredential
from app.services.auth_service import get_current_user
from app.services.crypto import encrypt_data, decrypt_data
from app.services.sniper_bridge import SniperBridge

router = APIRouter(prefix="/api/credentials", tags=["中研院憑證金庫"])

class SaveCredentialRequest(BaseModel):
    sinica_account: str # 身分證字號或帳號
    sinica_password: str # 密碼

@router.get("/")
def get_credential_status(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    cred = session.exec(select(SinicaCredential).where(SinicaCredential.user_id == user.id)).first()
    if not cred:
        return {
            "has_credential": False,
            "masked_account": None,
            "is_valid": False,
            "last_verified_at": None
        }
    
    try:
        raw_account = decrypt_data(cred.account_encrypted)
        masked = raw_account[:3] + "****" + raw_account[-2:] if len(raw_account) >= 5 else "***"
    except Exception:
        masked = "***"

    return {
        "has_credential": True,
        "masked_account": masked,
        "is_valid": cred.is_valid,
        "last_verified_at": cred.last_verified_at
    }

@router.post("/save")
async def save_and_verify_credential(
    req: SaveCredentialRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    cred = session.exec(select(SinicaCredential).where(SinicaCredential.user_id == user.id)).first()
    if not cred:
        cred = SinicaCredential(
            user_id=user.id,
            account_encrypted=encrypt_data(req.sinica_account),
            password_encrypted=encrypt_data(req.sinica_password)
        )
    else:
        cred.account_encrypted = encrypt_data(req.sinica_account)
        cred.password_encrypted = encrypt_data(req.sinica_password)
        cred.updated_at = datetime.utcnow()

    # 即時背景自動登入驗證
    ok, msg, state_path = await SniperBridge.auto_login_and_save_state(cred)
    cred.is_valid = ok
    cred.state_file_path = state_path
    cred.last_verified_at = datetime.utcnow()
    
    session.add(cred)
    session.commit()
    session.refresh(cred)
    
    return {
        "success": ok,
        "message": msg,
        "is_valid": cred.is_valid,
        "last_verified_at": cred.last_verified_at
    }

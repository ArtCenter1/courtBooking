import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.services.crypto import encrypt_data, decrypt_data
from app.services.scheduler import TaskScheduler
from app.models.booking_task import BookingTask

# 測試用記憶體 SQLite 資料庫
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_crypto_encryption_and_decryption():
    raw_text = "A123456789_SecretPassword"
    encrypted = encrypt_data(raw_text)
    assert encrypted != raw_text
    decrypted = decrypt_data(encrypted)
    assert decrypted == raw_text

def test_auth_and_user_flow(client: TestClient):
    # 1. 註冊
    reg_res = client.post("/api/auth/register", json={
        "email": "tester@example.com",
        "password": "strong_password_123",
        "name": "網球愛好者"
    })
    assert reg_res.status_code == 200
    token = reg_res.json()["access_token"]
    assert token is not None

    # 2. 獲取個人資訊
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "tester@example.com"
    assert me_res.json()["name"] == "網球愛好者"

    # 3. 登入
    login_res = client.post("/api/auth/login", json={
        "email": "tester@example.com",
        "password": "strong_password_123"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

def test_anti_conflict_resolution():
    scheduler = TaskScheduler()
    # 構造兩個同時段任務
    task1 = BookingTask(
        id=1,
        user_id=101,
        target_date="09/06",
        target_day_num="06",
        primary_slots_json='["17:00", "18:00"]',
        court_order_json='["A", "B"]'
    )
    task2 = BookingTask(
        id=2,
        user_id=102,
        target_date="09/06",
        target_day_num="06",
        primary_slots_json='["17:00", "18:00"]',
        court_order_json='["A", "B"]'
    )
    
    resolved = scheduler.resolve_conflicts([task1, task2])
    assert resolved[0].court_order == ["A", "B"]
    # Task2 避讓至 B 場優先
    assert resolved[1].court_order == ["B", "A"]

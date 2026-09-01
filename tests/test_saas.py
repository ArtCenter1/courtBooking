import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.services.crypto import encrypt_data, decrypt_data
from app.services.scheduler import TaskScheduler
from app.models.booking_task import BookingTask

class TestCourtBookingSaaS(unittest.TestCase):
    def setUp(self):
        # 測試用記憶體 SQLite 資料庫
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        def get_session_override():
            return self.session

        app.dependency_overrides[get_session] = get_session_override
        self.client = TestClient(app)

    def tearDown(self):
        self.session.close()
        app.dependency_overrides.clear()

    def test_crypto_encryption_and_decryption(self):
        raw_text = "A123456789_SecretPassword"
        encrypted = encrypt_data(raw_text)
        self.assertNotEqual(encrypted, raw_text)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(decrypted, raw_text)

    def test_auth_and_user_flow(self):
        # 1. 註冊
        reg_res = self.client.post("/api/auth/register", json={
            "email": "tester@example.com",
            "password": "strong_password_123",
            "name": "網球愛好者"
        })
        self.assertEqual(reg_res.status_code, 200)
        token = reg_res.json().get("access_token")
        self.assertIsNotNone(token)

        # 2. 獲取個人資訊
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["email"], "tester@example.com")
        self.assertEqual(me_res.json()["name"], "網球愛好者")

        # 3. 登入
        login_res = self.client.post("/api/auth/login", json={
            "email": "tester@example.com",
            "password": "strong_password_123"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("access_token", login_res.json())

    def test_anti_conflict_resolution(self):
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
        self.assertEqual(resolved[0].court_order, ["A", "B"])
        # Task2 避讓至 B 場優先
        self.assertEqual(resolved[1].court_order, ["B", "A"])

if __name__ == "__main__":
    unittest.main()

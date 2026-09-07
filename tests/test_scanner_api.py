import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session

class TestRadarAPI(unittest.TestCase):
    def setUp(self):
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

        # 註冊測試帳號並取得 Token
        reg_res = self.client.post("/api/auth/register", json={
            "email": "radar@example.com",
            "password": "pass",
            "name": "RadarTester"
        })
        self.token = reg_res.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.session.close()
        app.dependency_overrides.clear()

    @patch("src.scanner.CalendarScanner.scan_day_slots")
    def test_scan_slots_success(self, mock_scan):
        # Mock scanner 返回的結構
        mock_scan.return_value = {
            "A": [
                {
                    "dayNum": "05",
                    "isTarget": True,
                    "slots": [
                        {"startTime": "17:00", "title": "17:00~18:00", "text": "17~18", "isAvailable": True},
                        {"startTime": "18:00", "title": "18:00~19:00", "text": "已預約", "isAvailable": False}
                    ]
                }
            ],
            "B": [
                {
                    "dayNum": "05",
                    "isTarget": True,
                    "slots": [
                        {"startTime": "17:00", "title": "17:00~18:00", "text": "開放", "isAvailable": False}
                    ]
                }
            ]
        }

        # 呼叫 Radar API
        res = self.client.post("/api/scanner/slots", json={
            "day": "05",
            "court": "ALL",
            "requested_slots": ["17:00", "18:00"]
        }, headers=self.headers)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["target_day"], "05")
        self.assertEqual(len(data["all_open_slots"]), 1)
        self.assertEqual(data["all_open_slots"][0]["startTime"], "17:00")
        self.assertEqual(data["all_open_slots"][0]["court"], "A")
        
        # 志願命中測試
        self.assertTrue(data["has_matching_available"])
        self.assertEqual(len(data["matched_open_slots"]), 1)

if __name__ == "__main__":
    unittest.main()

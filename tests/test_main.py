from fastapi.testclient import TestClient
from app.main import app
import datetime

client = TestClient(app)


def test_root():
    """測試根路徑"""
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()
    assert r.json()["status"] == "running"


def test_health_check():
    """測試健康檢查"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_logs_missing_required_fields():
    """測試缺少必填欄位的情況"""
    r = client.get("/logs?riskLevel=1&type=1")
    assert r.status_code == 400
    assert "detail" in r.json()


def test_get_logs_list():
    """測試日誌列表查詢"""
    r = client.get("/logs/list?limit=10&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "data" in data
    assert "count" in data


def test_get_logs_list_with_filters():
    """測試帶篩選的日誌列表查詢"""
    r = client.get("/logs/list?riskLevel=1&location=test&limit=10")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"


def test_get_logs_statistics():
    """測試日誌統計"""
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    r = client.get(f"/logs/statistics?date_from={week_ago}&date_to={today}")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "total_logs" in data
    assert "by_risk_level" in data
    assert "by_location" in data

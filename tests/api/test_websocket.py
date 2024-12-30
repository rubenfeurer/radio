import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from config.config import settings
from unittest.mock import MagicMock, patch
from src.core.models import SystemStatus

@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket status updates"""
    client = TestClient(app)
    with client.websocket_connect(f"{settings.API_V1_STR}/ws") as ws:
        # Get initial status
        status = ws.receive_json()
        assert status["type"] == "status_response"
        assert "data" in status
        assert "volume" in status["data"]
        assert "is_playing" in status["data"]
        assert isinstance(status["data"]["volume"], int)
        assert isinstance(status["data"]["is_playing"], bool)

if __name__ == "__main__":
    pytest.main(["-v", "-k", "websocket"])
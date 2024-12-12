import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app

client = TestClient(app)

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._run_command')
async def test_connect_to_preconfigured_success(mock_run_command):
    """Test successful connection to preconfigured network"""
    # Mock successful connection
    mock_run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # nmcli connection up
        MagicMock(returncode=0, stdout="100 (connected)")  # verify connection
    ]
    
    response = client.post("/api/v1/wifi/connect/preconfigured")
    assert response.status_code == 200
    assert "Successfully connected" in response.json()["message"]

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._run_command')
async def test_connect_to_preconfigured_failure(mock_run_command):
    """Test failed connection to preconfigured network"""
    mock_run_command.return_value = MagicMock(
        returncode=1, 
        stderr="Connection activation failed"
    )
    
    response = client.post("/api/v1/wifi/connect/preconfigured")
    assert response.status_code == 400
    assert "Failed to connect" in response.json()["detail"]

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._run_command')
async def test_connect_to_preconfigured_verify_failure(mock_run_command):
    """Test connection verification failure"""
    mock_run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # nmcli connection up succeeds
        MagicMock(returncode=0, stdout="20 (unavailable)")  # verify connection fails
    ]
    
    response = client.post("/api/v1/wifi/connect/preconfigured")
    assert response.status_code == 400
    assert "Failed to verify connection" in response.json()["detail"] 
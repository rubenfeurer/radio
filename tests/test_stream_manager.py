import pytest
from src.utils.stream_manager import StreamManager
import os
import json
import toml

@pytest.fixture
def sample_streams():
    return {
        "links": [
            {"name": "Test Station 1", "url": "http://test1.com/stream"},
            {"name": "Test Station 2", "url": "http://test2.com/stream"},
            {"name": "Test Station 3", "url": "http://test3.com/stream"}
        ]
    }

@pytest.fixture
def sample_radio_state():
    return {
        "selected_stations": [
            {"name": "Test Station 1", "url": "http://test1.com/stream"},
            {"name": "Test Station 2", "url": "http://test2.com/stream"},
            {"name": "Test Station 3", "url": "http://test3.com/stream"}
        ]
    }

@pytest.fixture
def stream_manager(sample_streams, sample_radio_state, tmp_path):
    config_path = tmp_path / "streams.toml"
    state_path = tmp_path / "radio_state.json"
    
    with open(config_path, "w") as f:
        toml.dump(sample_streams, f)
    
    with open(state_path, "w") as f:
        json.dump(sample_radio_state, f)
    
    return StreamManager(toml_file=str(config_path), state_file=str(state_path))

def test_load_streams(stream_manager):
    streams = stream_manager.streams
    assert len(streams) == 3
    assert streams[0]["name"] == "Test Station 1"
    assert streams[0]["url"] == "http://test1.com/stream"

def test_get_streams_by_slots(stream_manager):
    """Test that get_streams_by_slots returns the stations from radio_state.json"""
    streams = stream_manager.get_streams_by_slots()
    assert len(streams) == 3
    assert streams[1] == "http://test1.com/stream"
    assert streams[2] == "http://test2.com/stream"
    assert streams[3] == "http://test3.com/stream"

def test_get_streams_by_slots_with_missing_state_file(stream_manager, tmp_path):
    """Test fallback behavior when radio_state.json is missing"""
    os.remove(tmp_path / "radio_state.json")
    
    streams = stream_manager.get_streams_by_slots()
    assert len(streams) == 3
    assert streams[1] == "http://test1.com/stream"
    assert streams[2] == "http://test2.com/stream"
    assert streams[3] == "http://test3.com/stream"

def test_get_streams_by_slots_with_invalid_state_file(stream_manager, tmp_path):
    """Test fallback behavior when radio_state.json is invalid"""
    with open(tmp_path / "radio_state.json", "w") as f:
        f.write("invalid json")
    
    streams = stream_manager.get_streams_by_slots()
    assert len(streams) == 3
    assert streams[1] == "http://test1.com/stream"
    assert streams[2] == "http://test2.com/stream"
    assert streams[3] == "http://test3.com/stream"
  
import pytest
from unittest.mock import Mock
import time
from src.hardware.button_handler import ButtonMapper, ButtonStateHandler, StreamToggler, ButtonPress

def test_button_press_dataclass():
    """Test ButtonPress dataclass creation and attributes"""
    press = ButtonPress(channel=17, button_index=1)
    assert press.channel == 17
    assert press.button_index == 1
    assert press.stream_url is None

class TestButtonMapper:
    def test_valid_button_mapping(self):
        """Test mapping of valid GPIO channels to button indices"""
        assert ButtonMapper.get_button_index(17) == 1
        assert ButtonMapper.get_button_index(16) == 2
        assert ButtonMapper.get_button_index(26) == 3

    def test_invalid_button_mapping(self):
        """Test mapping of invalid GPIO channels"""
        assert ButtonMapper.get_button_index(99) is None
        assert ButtonMapper.get_button_index(0) is None

class TestButtonStateHandler:
    def test_initial_press_allowed(self):
        """Test that first press is always allowed"""
        handler = ButtonStateHandler()
        assert handler.should_process() is True

    def test_debounce_blocks_rapid_presses(self):
        """Test that rapid presses are blocked"""
        handler = ButtonStateHandler()
        assert handler.should_process() is True  # First press
        assert handler.should_process() is False  # Immediate second press

    def test_debounce_allows_after_wait(self):
        """Test that presses are allowed after debounce time"""
        handler = ButtonStateHandler()
        assert handler.should_process() is True  # First press
        time.sleep(0.4)  # Wait longer than debounce time
        assert handler.should_process() is True  # Should allow press after wait

class TestStreamToggler:
    @pytest.fixture
    def mock_player(self):
        player = Mock()
        player._status = {
            "state": "stopped",
            "current_station": None,
            "volume": 80
        }
        
        def get_status():
            return player._status.copy()
        
        def play(stream):
            player._status.update({
                "state": "playing",
                "current_station": stream
            })
            
        def stop():
            player._status.update({
                "state": "stopped",
                "current_station": None
            })
            
        player.get_status = Mock(side_effect=get_status)
        player.play = Mock(side_effect=play)
        player.stop = Mock(side_effect=stop)
        return player

    @pytest.fixture
    def mock_stream_manager(self):
        manager = Mock()
        streams = {
            1: "http://test1.com/stream",
            2: "http://test2.com/stream",
            3: "http://test3.com/stream"
        }
        manager.get_streams_by_slots = Mock(return_value=streams)
        return manager

    @pytest.fixture
    def stream_toggler(self, mock_player, mock_stream_manager):
        return StreamToggler(mock_player, mock_stream_manager)

    def test_play_stream_when_nothing_playing(self, stream_toggler, mock_player):
        """Test playing a stream when nothing is currently playing"""
        button_press = ButtonPress(channel=17, button_index=1)
        stream_toggler.handle_button_press(button_press)
        
        mock_player.play.assert_called_once_with("http://test1.com/stream")
        assert mock_player.stop.call_count == 0

    def test_stop_stream_when_same_stream_playing(self, stream_toggler, mock_player):
        """Test stopping a stream when pressing the same button again"""
        # First press to start playing
        button_press = ButtonPress(channel=17, button_index=1)
        stream_toggler.handle_button_press(button_press)
        
        # Reset mock call history
        mock_player.play.reset_mock()
        mock_player.stop.reset_mock()
        
        # Second press should stop
        stream_toggler.handle_button_press(button_press)
        
        mock_player.stop.assert_called_once()
        assert mock_player.play.call_count == 0

    def test_switch_streams(self, stream_toggler, mock_player):
        """Test switching from one stream to another"""
        # Start playing first stream
        button_press1 = ButtonPress(channel=17, button_index=1)
        stream_toggler.handle_button_press(button_press1)
        
        # Reset mock call history
        mock_player.play.reset_mock()
        mock_player.stop.reset_mock()
        
        # Switch to second stream
        button_press2 = ButtonPress(channel=16, button_index=2)
        stream_toggler.handle_button_press(button_press2)
        
        assert mock_player.stop.call_count == 1
        mock_player.play.assert_called_once_with("http://test2.com/stream")

    def test_invalid_button_index(self, stream_toggler, mock_player):
        """Test handling of invalid button index"""
        button_press = ButtonPress(channel=99, button_index=99)
        stream_toggler.handle_button_press(button_press)
        
        assert mock_player.play.call_count == 0
        assert mock_player.stop.call_count == 0 
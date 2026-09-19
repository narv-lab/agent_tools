import pytest
from unittest.mock import patch, MagicMock
from collaboration.service import CollaborationService

@patch("builtins.input", return_value="user response")
def test_ask_human_sync(mock_input):
    svc = CollaborationService()
    res = svc.ask_human_sync("Test question?")
    assert res == "user response"
    mock_input.assert_called_once()

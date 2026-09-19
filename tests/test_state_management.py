import pytest
from unittest.mock import patch, MagicMock
from state_management.manager import _run_git

@patch("state_management.manager.ExecutionService")
def test_run_git(mock_exec_cls):
    mock_svc = MagicMock()
    mock_exec_cls.return_value = mock_svc
    
    mock_res = MagicMock()
    mock_res.exit_code = 0
    mock_res.stdout = "branch1"
    mock_res.stderr = ""
    mock_svc.execute_bash.return_value = mock_res
    
    res = _run_git(["branch", "--show-current"], capture_output=True, text=True)
    
    assert res.returncode == 0
    assert res.stdout == "branch1"
    assert res.stderr == ""

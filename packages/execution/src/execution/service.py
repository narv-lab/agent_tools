import os
import pty
import select
import signal
import subprocess
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
import logging

def _get_cwd() -> str:
    cwd = os.environ.get("AGENT_WORKSPACE_CWD", os.getcwd())
    return cwd


from execution.models import (
    TestResult, BashResult, SpawnResult, ProcessOutput, SuccessResult, ErrorResult
)
from execution.exceptions import (
    ExecutionError, InvalidProcessId, CommandExecutionFailed
)

logger = logging.getLogger(__name__)

class ManagedProcess:
    def __init__(self, command: str, use_pty: bool, env: Dict[str, str]):
        self.command = command
        self.use_pty = use_pty
        self.env = env
        self.process = None
        self.master_fd = None
        self.output_buffer = bytearray()
        self.lock = threading.Lock()
        self.is_waiting_for_input = False
        
        self._start()

    def _start(self):
        env = os.environ.copy()
        env.update(self.env)
        
        cwd = os.environ.get("AGENT_WORKSPACE_CWD", os.getcwd())
        
        if self.use_pty:
            self.master_fd, slave_fd = pty.openpty()
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                cwd=cwd,
                close_fds=True,
                preexec_fn=os.setsid
            )
            os.close(slave_fd)
        else:
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=cwd,
                preexec_fn=os.setsid
            )
            self.master_fd = self.process.stdout.fileno()

        self.reader_thread = threading.Thread(target=self._reader, daemon=True)
        self.reader_thread.start()

    def _reader(self):
        try:
            while True:
                r, w, e = select.select([self.master_fd], [], [], 0.5)
                if self.master_fd in r:
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        break
                    with self.lock:
                        self.output_buffer.extend(data)
                        self.is_waiting_for_input = self._check_waiting_input()
                elif self.process.poll() is not None:
                    # check one last time
                    r, w, e = select.select([self.master_fd], [], [], 0.1)
                    if self.master_fd in r:
                        data = os.read(self.master_fd, 4096)
                        if data:
                            with self.lock:
                                self.output_buffer.extend(data)
                    break
                else:
                    with self.lock:
                        self.is_waiting_for_input = self._check_waiting_input()
        except OSError:
            pass
            
    def _check_waiting_input(self) -> bool:
        try:
            tail = self.output_buffer[-50:].decode('utf-8', errors='ignore')
            if any(tail.endswith(p) for p in (": ", "? ", "$ ", "> ", "# ", "Password: ")):
                return True
        except Exception:
            pass
        return False

    def read_output(self, offset: int) -> Tuple[str, int, bool]:
        with self.lock:
            data = self.output_buffer[offset:]
            log = data.decode('utf-8', errors='ignore')
            next_offset = offset + len(data)
            return log, next_offset, self.is_waiting_for_input

    def send_input(self, input_str: str):
        data = input_str.encode('utf-8')
        if self.use_pty:
            os.write(self.master_fd, data)
        else:
            if self.process.stdin:
                self.process.stdin.write(data)
                self.process.stdin.flush()
        
        with self.lock:
            self.is_waiting_for_input = False

    def kill(self):
        if self.process and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                time.sleep(0.1)
                if self.process.poll() is None:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except OSError:
                pass


class ExecutionService:
    def __init__(self):
        self._processes: Dict[str, ManagedProcess] = {}

    def run_tests(self, test_target: str, overrides: Dict[str, str]) -> Union[List[TestResult], ErrorResult]:
        env = os.environ.copy()
        env.update(overrides)
        
        cmd = f"pytest {test_target} -v --tb=short"
        try:
            result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
        except Exception as e:
            # pytest startup failure (OSError, etc.) -- returned as L1 Error(Message: String) (FINDING-003)
            return ErrorResult(error=f"Failed to run tests: {e}")
        
        res = TestResult(
            test_name=test_target,
            passed=(result.returncode == 0),
            message=result.stdout[-1000:] if result.stdout else "No stdout",
            trace=[result.stderr] if result.stderr else None
        )
        return [res]

    def execute_bash(
        self, script: str, timeout_ms: int, profile: Any, overrides: Dict[str, str]
    ) -> Union[BashResult, dict]:
        """
        Executes a shell script and returns a BashResult.
        Unrecoverable errors such as process startup failures do not propagate exceptions,
        but return {'error': message} (L0 Explicit error reporting principle / FINDING-003).
        On timeout, returns a BashResult with exit_code=-1.
        """
        env = os.environ.copy()
        env.update(overrides)

        cwd = os.environ.get("AGENT_WORKSPACE_CWD", os.getcwd())

        try:
            process = subprocess.Popen(
                script,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=cwd,
                preexec_fn=os.setsid
            )
        except Exception as e:
            # Process startup failure (OSError, FileNotFoundError, etc.)
            return ErrorResult(error=f"Failed to spawn process: {e}")

        try:
            stdout_data, stderr_data = process.communicate(timeout=timeout_ms / 1000.0)
            return BashResult(
                stdout=stdout_data.decode('utf-8', errors='ignore'),
                stderr=stderr_data.decode('utf-8', errors='ignore'),
                exit_code=process.returncode
            )
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except OSError:
                process.kill()
            stdout_data, stderr_data = process.communicate()
            return BashResult(
                stdout=stdout_data.decode('utf-8', errors='ignore'),
                stderr=stderr_data.decode('utf-8', errors='ignore') + f"\n[Timeout after {timeout_ms}ms]",
                exit_code=-1
            )
        except Exception as e:
            return ErrorResult(error=f"Unexpected error during execution: {e}")

    def spawn_process(
        self, command: str, use_pty: bool, profile: Any, overrides: Dict[str, str]
    ) -> Union[SpawnResult, dict]:
        """
        Spawns a process and returns a SpawnResult.
        On startup failure, returns {'error': message} (FINDING-003).
        """
        try:
            proc_id = str(uuid.uuid4())
            self._processes[proc_id] = ManagedProcess(command, use_pty, overrides)
            return SpawnResult(process_id=proc_id)
        except Exception as e:
            return ErrorResult(error=f"Failed to spawn process: {e}")

    def read_process_output(self, process_id: str, offset: int) -> ProcessOutput:
        if process_id not in self._processes:
            raise InvalidProcessId(process_id)
            
        log, next_offset, waiting = self._processes[process_id].read_output(offset)
        return ProcessOutput(log=log, next_offset=next_offset, is_waiting_for_input=waiting)

    def send_input_to_process(self, process_id: str, input_str: str) -> SuccessResult:
        if process_id not in self._processes:
            raise InvalidProcessId(process_id)
            
        try:
            self._processes[process_id].send_input(input_str)
            return SuccessResult(success=True)
        except Exception as e:
            return SuccessResult(success=False, error_reason=str(e))

    def kill_process(self, process_id: str) -> SuccessResult:
        if process_id not in self._processes:
            raise InvalidProcessId(process_id)
            
        try:
            self._processes[process_id].kill()
            del self._processes[process_id]
            return SuccessResult(success=True)
        except Exception as e:
            return SuccessResult(success=False, error_reason=str(e))

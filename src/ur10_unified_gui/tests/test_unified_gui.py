import json
import queue
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import main as gui
from config_schema import UnifiedGUIConfig


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(gui.UnifiedGUIApp, "_poll", lambda self: None)
    warnings = []
    errors = []
    monkeypatch.setattr(gui.UnifiedGUIApp, "_show_warning", lambda self, t, m: warnings.append((t, m)))
    monkeypatch.setattr(gui.UnifiedGUIApp, "_show_error", lambda self, t, m: errors.append((t, m)))
    app = gui.UnifiedGUIApp()
    app.withdraw()
    app._test_warnings = warnings
    app._test_errors = errors
    yield app
    app.destroy()


def test_real_network_check_pass_with_warnings(app, monkeypatch):
    cfg = app._gather_real()
    cfg.host_ip = "192.168.56.1"
    cfg.robot_ip = "192.168.56.101"
    cfg.robot_subnet = "192.168.56.0/24"
    cfg.run_full_verify_script = "/tmp/fake_run_full_verify.sh"

    monkeypatch.setattr(gui, "_file_exists", lambda p: p == cfg.run_full_verify_script)
    monkeypatch.setattr(app, "_run_ping", lambda _ip: SimpleNamespace(returncode=1))
    monkeypatch.setattr(app, "_tcp_check", lambda _ip, _port, timeout=1.0: False)

    ok = app._check_real_network(cfg)
    assert ok is True
    assert app.status_var.get().startswith("WARN")
    assert any("network_check_pass_with_warnings" in app.txt.get("1.0", "end") for _ in [0])


def test_real_network_check_invalid_ip_rejected(app):
    cfg = app._gather_real()
    cfg.host_ip = "invalid"
    ok = app._check_real_network(cfg)
    assert ok is False
    assert app._test_errors


def test_sim_network_check_workspace_dir_validation(app):
    cfg = app._gather_sim()
    cfg.workspace_root = "/path/does/not/exist"
    ok = app._check_sim_network(cfg)
    assert ok is False
    assert app.status_var.get().startswith("FAIL")


def test_mutex_blocks_second_start(app, monkeypatch, tmp_path):
    cfg = app._gather_sim()
    cfg.workspace_root = str(tmp_path)
    cfg.ur_type = "ur10"
    cfg.world = str(tmp_path / "dummy.world")
    (tmp_path / "dummy.world").write_text("", encoding="utf-8")

    monkeypatch.setattr(app, "_gather_sim", lambda: cfg)
    monkeypatch.setattr(app, "_check_sim_network", lambda _cfg: True)

    class DummySession:
        def __init__(self, *args, **kwargs):
            self._running = True

        def start(self):
            return None

        def is_running(self):
            return self._running

        def stop(self, term_timeout=2.5):
            self._running = False

    monkeypatch.setattr(gui, "ProcessSession", DummySession)

    app._start_sim()
    assert app.current_session is not None
    app._start_real()
    assert app._test_warnings
    assert "拒绝启动" in app.txt.get("1.0", "end")


def test_stop_session_running_and_idle(app):
    class DummySession:
        def __init__(self):
            self.stopped = False

        def stop(self, term_timeout=2.5):
            self.stopped = True

        def is_running(self):
            return True

    s = DummySession()
    app.current_session = s
    app.active_mode = "Sim"
    app._stop_session()
    assert s.stopped is True
    assert app.current_session is None
    assert app.status_var.get().startswith("STOPPED")

    app._stop_session()
    assert app.status_var.get().startswith("STOPPED")


def test_summary_and_exit_fallback(app):
    app._prepare_run_state("Real")
    app.current_session = SimpleNamespace(is_running=lambda: False, proc=SimpleNamespace(poll=lambda: 0))
    app._append_log("Real", "[SUMMARY] state=PASS reason=ok")
    assert app.status_var.get().startswith("PASS")

    app._prepare_run_state("Real")
    app.current_session = SimpleNamespace(is_running=lambda: False, proc=SimpleNamespace(poll=lambda: 1))
    app.last_summary_state = None
    app._append_log("Real", "[ERROR] connection failed")
    app._append_log("Real", "[INFO] Process exit=1")
    assert app.status_var.get().startswith("FAIL")


def test_config_save_load_roundtrip(app, monkeypatch, tmp_path):
    cfg_path = tmp_path / "cfg.json"
    monkeypatch.setattr(gui, "CONFIG_PATH", cfg_path)

    app.v_mode.set("Real")
    app.v_host_ip.set("10.0.0.1")
    app.v_robot_ip.set("10.0.0.2")
    app.v_robot_subnet.set("10.0.0.0/24")
    app.v_reverse_ip.set("10.0.0.3")
    app.v_workspace_root.set(str(tmp_path))

    app._save_config()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data["host_ip"] == "10.0.0.1"

    data["ur_type"] = "ur5"
    cfg_path.write_text(json.dumps(data), encoding="utf-8")
    app._load_config_to_ui()
    assert app.v_ur_type.get() == "ur5"


def test_real_start_fallback_script_used(app, monkeypatch, tmp_path):
    primary = tmp_path / "run_full_verify.sh"
    fallback = tmp_path / "run_full_verify_wsl.sh"
    fallback.write_text("#!/bin/bash\n", encoding="utf-8")

    cfg = UnifiedGUIConfig(
        mode="Real",
        host_ip="192.168.56.1",
        robot_ip="192.168.56.101",
        robot_subnet="192.168.56.0/24",
        reverse_ip="192.168.56.1",
        wrist3_delta="0.5",
        controller="scaled_joint_trajectory_controller",
        status_timeout="60",
        run_full_verify_script=str(primary),
        run_full_verify_wsl_script=str(fallback),
        workspace_root=str(tmp_path),
        auto_network_check=False,
    )

    monkeypatch.setattr(app, "_gather_real", lambda: cfg)

    captured = {}

    class DummySession:
        def __init__(self, cmd, cwd, env, label, log_queue):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            captured["env"] = env
            self._running = True

        def start(self):
            return None

        def is_running(self):
            return self._running

        def stop(self, term_timeout=2.5):
            self._running = False

    monkeypatch.setattr(gui, "ProcessSession", DummySession)

    app._start_real()
    cmd_str = " ".join(captured["cmd"])
    assert str(fallback) in cmd_str
    assert captured["env"]["ROBOT_IP"] == "192.168.56.101"


def test_process_session_uses_popen_patch(monkeypatch):
    q = queue.Queue()

    class FakeStdout:
        def __iter__(self):
            yield "line1\n"

    class FakeProc:
        def __init__(self):
            self.stdout = FakeStdout()
            self.pid = 12345

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    created = {}

    def fake_popen(*args, **kwargs):
        created["called"] = True
        return FakeProc()

    monkeypatch.setattr(gui.ProcessSession, "POPEN", staticmethod(fake_popen))

    s = gui.ProcessSession(["echo", "x"], cwd="/tmp", env=None, label="T", log_queue=q)
    s.start()
    assert created.get("called") is True

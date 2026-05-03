"""Unit tests for kubernetes_utils.py."""
import json
from unittest.mock import MagicMock, patch

import kubernetes_utils


def _mock_run_ok(stdout: str) -> MagicMock:
    r = MagicMock()
    r.returncode = 0
    r.stdout = stdout
    r.stderr = ""
    return r


def _mock_run_fail(stderr: str = "kubectl error") -> MagicMock:
    r = MagicMock()
    r.returncode = 1
    r.stdout = ""
    r.stderr = stderr
    return r


# ── is_available ───────────────────────────────────────────────────────────────

def test_is_available_true():
    with patch("shutil.which", return_value="/usr/bin/kubectl"):
        assert kubernetes_utils.is_available() is True


def test_is_available_false():
    with patch("shutil.which", return_value=None):
        assert kubernetes_utils.is_available() is False


# ── list_contexts ──────────────────────────────────────────────────────────────

def test_list_contexts_returns_names():
    with patch("subprocess.run", return_value=_mock_run_ok("ctx-prod\nctx-dev\n")):
        result = kubernetes_utils.list_contexts()
    assert result == ["ctx-prod", "ctx-dev"]


def test_list_contexts_strips_blank_lines():
    with patch("subprocess.run", return_value=_mock_run_ok("ctx1\n\nctx2\n")):
        result = kubernetes_utils.list_contexts()
    assert result == ["ctx1", "ctx2"]


def test_list_contexts_raises_on_error():
    with patch("subprocess.run", return_value=_mock_run_fail("no kubeconfig")):
        try:
            kubernetes_utils.list_contexts()
            assert False
        except RuntimeError as e:
            assert "no kubeconfig" in str(e)


# ── current_context ────────────────────────────────────────────────────────────

def test_current_context_returns_name():
    with patch("subprocess.run", return_value=_mock_run_ok("my-cluster\n")):
        assert kubernetes_utils.current_context() == "my-cluster"


# ── list_namespaces ────────────────────────────────────────────────────────────

def test_list_namespaces_returns_list():
    with patch("subprocess.run", return_value=_mock_run_ok("default kube-system monitoring")):
        result = kubernetes_utils.list_namespaces()
    assert result == ["default", "kube-system", "monitoring"]


def test_list_namespaces_with_context_passes_flag():
    with patch("subprocess.run", return_value=_mock_run_ok("default")) as mock_run:
        kubernetes_utils.list_namespaces(context="prod-ctx")
    call_args = mock_run.call_args[0][0]
    assert "--context" in call_args
    assert "prod-ctx" in call_args


def test_list_namespaces_no_context_no_flag():
    with patch("subprocess.run", return_value=_mock_run_ok("default")) as mock_run:
        kubernetes_utils.list_namespaces()
    call_args = mock_run.call_args[0][0]
    assert "--context" not in call_args


# ── list_pods ──────────────────────────────────────────────────────────────────

def test_list_pods_returns_name_and_phase():
    pods = {
        "items": [
            {"metadata": {"name": "app-abc"}, "status": {"phase": "Running"}},
            {"metadata": {"name": "app-def"}, "status": {"phase": "Pending"}},
        ]
    }
    with patch("subprocess.run", return_value=_mock_run_ok(json.dumps(pods))):
        result = kubernetes_utils.list_pods("default")
    assert len(result) == 2
    assert result[0] == {"name": "app-abc", "status": "Running"}
    assert result[1] == {"name": "app-def", "status": "Pending"}


def test_list_pods_missing_status_defaults_unknown():
    pods = {"items": [{"metadata": {"name": "pod-x"}, "status": {}}]}
    with patch("subprocess.run", return_value=_mock_run_ok(json.dumps(pods))):
        result = kubernetes_utils.list_pods("ns")
    assert result[0]["status"] == "Unknown"


def test_list_pods_empty_items():
    with patch("subprocess.run", return_value=_mock_run_ok(json.dumps({"items": []}))):
        assert kubernetes_utils.list_pods("default") == []


# ── build_logs_cmd ─────────────────────────────────────────────────────────────

def test_build_logs_cmd_basic():
    cmd = kubernetes_utils.build_logs_cmd("mypod", "default")
    assert cmd == ["kubectl", "logs", "-f", "mypod", "-n", "default", "--tail=200"]


def test_build_logs_cmd_with_context():
    cmd = kubernetes_utils.build_logs_cmd("mypod", "ns", context="prod")
    assert "--context" in cmd
    assert "prod" in cmd


def test_build_logs_cmd_with_container():
    cmd = kubernetes_utils.build_logs_cmd("mypod", "ns", container="sidecar")
    assert "-c" in cmd
    assert "sidecar" in cmd


def test_build_logs_cmd_custom_tail():
    cmd = kubernetes_utils.build_logs_cmd("mypod", "ns", tail=500)
    assert "--tail=500" in cmd


def test_build_logs_cmd_no_context_no_flag():
    cmd = kubernetes_utils.build_logs_cmd("pod", "ns")
    assert "--context" not in cmd


def test_build_logs_cmd_no_container_no_flag():
    cmd = kubernetes_utils.build_logs_cmd("pod", "ns")
    assert "-c" not in cmd

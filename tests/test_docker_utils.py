"""Unit tests for docker_utils.py."""
import json
from unittest.mock import MagicMock, patch

import docker_utils


def _mock_run_ok(stdout: str) -> MagicMock:
    r = MagicMock()
    r.returncode = 0
    r.stdout = stdout
    r.stderr = ""
    return r


def _mock_run_fail(stderr: str = "docker error") -> MagicMock:
    r = MagicMock()
    r.returncode = 1
    r.stdout = ""
    r.stderr = stderr
    return r


# ── _extract_label ─────────────────────────────────────────────────────────────

def test_extract_label_found():
    assert docker_utils._extract_label("com.docker.compose.project=myapp,foo=bar", "com.docker.compose.project") == "myapp"


def test_extract_label_not_found():
    assert docker_utils._extract_label("com.docker.compose.project=myapp", "missing") == ""


def test_extract_label_empty_string():
    assert docker_utils._extract_label("", "any") == ""


def test_extract_label_value_with_equals():
    assert docker_utils._extract_label("key=val=extra", "key") == "val=extra"


# ── is_docker_available ────────────────────────────────────────────────────────

def test_is_docker_available_true():
    with patch("shutil.which", return_value="/usr/bin/docker"):
        assert docker_utils.is_docker_available() is True


def test_is_docker_available_false():
    with patch("shutil.which", return_value=None):
        assert docker_utils.is_docker_available() is False


# ── list_containers ────────────────────────────────────────────────────────────

def test_list_containers_parses_json_lines():
    container = {
        "ID": "abc123def456xyz",
        "Names": "/my_container",
        "Image": "nginx:latest",
        "Status": "Up 5 minutes",
        "Labels": "com.docker.compose.project=myapp,com.docker.compose.service=web",
    }
    output = json.dumps(container) + "\n"
    with patch("subprocess.run", return_value=_mock_run_ok(output)):
        result = docker_utils.list_containers()
    assert len(result) == 1
    c = result[0]
    assert c["id"] == "abc123def456"
    assert c["name"] == "my_container"
    assert c["image"] == "nginx:latest"
    assert c["compose_project"] == "myapp"
    assert c["compose_service"] == "web"


def test_list_containers_empty_output():
    with patch("subprocess.run", return_value=_mock_run_ok("")):
        assert docker_utils.list_containers() == []


def test_list_containers_skips_invalid_json_lines():
    good = json.dumps({"ID": "aaa", "Names": "/c", "Image": "img", "Status": "Up", "Labels": ""})
    output = "not-json\n" + good + "\n"
    with patch("subprocess.run", return_value=_mock_run_ok(output)):
        result = docker_utils.list_containers()
    assert len(result) == 1


def test_list_containers_raises_on_docker_error():
    with patch("subprocess.run", return_value=_mock_run_fail("permission denied")):
        try:
            docker_utils.list_containers()
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "permission denied" in str(e)


def test_list_containers_no_labels():
    container = {"ID": "deadbeef", "Names": "/solo", "Image": "alpine", "Status": "Up", "Labels": ""}
    with patch("subprocess.run", return_value=_mock_run_ok(json.dumps(container))):
        result = docker_utils.list_containers()
    assert result[0]["compose_project"] == ""
    assert result[0]["compose_service"] == ""


# ── list_compose_stacks ────────────────────────────────────────────────────────

def test_list_compose_stacks_returns_running():
    stacks = [
        {"Name": "webapp", "Status": "running(3)", "ConfigFiles": "/app/docker-compose.yml"},
        {"Name": "stopped", "Status": "exited(1)", "ConfigFiles": "/other/docker-compose.yml"},
    ]
    with patch("subprocess.run", return_value=_mock_run_ok(json.dumps(stacks))):
        result = docker_utils.list_compose_stacks()
    assert len(result) == 1
    assert result[0]["name"] == "webapp"


def test_list_compose_stacks_returns_empty_on_failure():
    with patch("subprocess.run", return_value=_mock_run_fail("docker compose not found")):
        result = docker_utils.list_compose_stacks()
    assert result == []


def test_list_compose_stacks_empty_json():
    with patch("subprocess.run", return_value=_mock_run_ok("[]")):
        assert docker_utils.list_compose_stacks() == []


def test_list_compose_stacks_empty_output():
    with patch("subprocess.run", return_value=_mock_run_ok("")):
        assert docker_utils.list_compose_stacks() == []

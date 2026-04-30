"""Unit tests for CLI argument parsing (mirrors the parser in main.py)."""
import argparse

import pytest

# ── Replicate the parser defined in main.py ───────────────────────────────────

def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--split",
        choices=["tab", "vertical", "horizontal"],
        default="tab",
    )
    parser.add_argument("--tail", type=int, default=100)
    parser.add_argument("files", nargs="*")
    return parser


def _parse(argv: list[str]) -> argparse.Namespace:
    args, _ = _make_parser().parse_known_args(argv)
    return args


# ── defaults ──────────────────────────────────────────────────────────────────

def test_defaults():
    args = _parse([])
    assert args.split == "tab"
    assert args.tail == 100
    assert args.files == []


# ── --split ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", ["tab", "vertical", "horizontal"])
def test_split_valid_modes(mode):
    args = _parse(["--split", mode])
    assert args.split == mode


def test_split_invalid_mode_raises():
    with pytest.raises(SystemExit):
        _make_parser().parse_args(["--split", "diagonal"])


# ── --tail ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("n", [1, 50, 100, 500, 50_000])
def test_tail_values(n):
    args = _parse(["--tail", str(n)])
    assert args.tail == n


def test_tail_non_integer_raises():
    with pytest.raises(SystemExit):
        _make_parser().parse_args(["--tail", "abc"])


# ── positional files ──────────────────────────────────────────────────────────

def test_single_file():
    args = _parse(["app.log"])
    assert args.files == ["app.log"]


def test_multiple_files():
    args = _parse(["a.log", "b.log", "c.log"])
    assert args.files == ["a.log", "b.log", "c.log"]


# ── combinations ─────────────────────────────────────────────────────────────

def test_combined_all_options():
    args = _parse(["--split", "horizontal", "--tail", "250", "svc-a.log", "svc-b.log"])
    assert args.split == "horizontal"
    assert args.tail == 250
    assert args.files == ["svc-a.log", "svc-b.log"]


def test_files_before_flags():
    """parse_known_args must handle flags appearing after positional args."""
    args = _parse(["app.log", "--tail", "200"])
    assert args.tail == 200
    assert "app.log" in args.files

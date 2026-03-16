"""Shared pytest configuration and fixtures.

Adds --runslow flag to control execution of slow tests (Hypothesis fuzz,
integration tests requiring external services).

Usage:
    uv run python -m pytest                   # fast tests only (skips slow)
    uv run python -m pytest --runslow         # all tests including slow
    uv run python -m pytest -m slow           # only slow tests
    uv run python -m pytest -m "not slow"     # explicit skip slow
"""
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow tests (Hypothesis fuzz, integration tests)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: mark test as slow (Hypothesis fuzz, integration)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--runslow"):
        return  # --runslow given: run everything

    skip_slow = pytest.mark.skip(reason="slow test — use --runslow to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)

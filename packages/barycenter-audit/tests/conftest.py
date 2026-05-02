"""Shared pytest fixtures for audit SDK tests."""
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_sql():
    conn = MagicMock(name="sql_conn")
    cur = MagicMock(name="cursor")
    conn.cursor.return_value = cur
    return conn


@pytest.fixture
def mock_la_sink():
    return MagicMock(name="la_sink")


@pytest.fixture
def mock_worm_sink():
    return MagicMock(name="worm_sink")

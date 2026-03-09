"""Tests for MCP tool registration — verify all tools are listed."""
import pytest
import asyncio
from open_medicine.mcp.server import handle_list_tools


@pytest.fixture
def tools():
    return asyncio.get_event_loop().run_until_complete(handle_list_tools())


def test_tool_count(tools):
    """Should have 9 tools (original 4 + 4 workflow + 1 unified search)."""
    assert len(tools) == 9


def test_new_differential_tools_exist(tools):
    """New differential tools should be registered."""
    names = [t.name for t in tools]
    assert "search_differential_diagnosis" in names
    assert "get_differential_diagnosis" in names


def test_new_pathway_tools_exist(tools):
    """New pathway tools should be registered."""
    names = [t.name for t in tools]
    assert "search_treatment_pathways" in names
    assert "get_treatment_pathway" in names


def test_search_medical_knowledge_tool_exists(tools):
    """Unified search tool should be registered."""
    names = [t.name for t in tools]
    assert "search_medical_knowledge" in names

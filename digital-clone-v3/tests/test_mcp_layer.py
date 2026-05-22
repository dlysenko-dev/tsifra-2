"""
Tests for MCPLayer (core/mcp_layer.py)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from core.mcp_layer import MCPLayer, MCPToolType


class TestMCPLayer:
    """Test suite for MCP Layer."""

    @pytest.fixture
    def mcp(self):
        return MCPLayer()

    def test_init_registers_default_tools(self, mcp):
        """Default tools should be registered on init."""
        assert len(mcp.tools) > 0
        assert "browser_navigate" in mcp.tools
        assert "file_read" in mcp.tools
        assert "shell_exec" in mcp.tools

    def test_register_tool(self, mcp):
        """Test custom tool registration."""
        from core.mcp_layer import MCPTool
        
        async def dummy_handler():
            return "ok"
        
        tool = MCPTool(
            name="test_tool",
            tool_type=MCPToolType.SEARCH,
            description="Test tool",
            parameters={},
            handler=dummy_handler,
        )
        mcp.register_tool(tool)
        assert "test_tool" in mcp.tools

    @pytest.mark.asyncio
    async def test_execute_existing_tool(self, mcp):
        """Execute a known tool."""
        result = await mcp.execute("file_list", {"path": "."})
        assert result.success is True
        assert isinstance(result.result, list)

    @pytest.mark.asyncio
    async def test_execute_missing_tool(self, mcp):
        """Execute a non-existent tool."""
        result = await mcp.execute("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_missing_params(self, mcp):
        """Execute tool without required params."""
        result = await mcp.execute("browser_navigate", {})
        assert result.success is False
        assert "Missing required params" in result.error

    def test_get_tool_descriptions(self, mcp):
        """Tool descriptions for LLM prompts."""
        desc = mcp.get_tool_descriptions()
        assert "browser_navigate" in desc
        assert "file_read" in desc

    def test_get_tools_by_type(self, mcp):
        """Filter tools by type."""
        browser_tools = mcp.get_tools_by_type(MCPToolType.BROWSER)
        assert len(browser_tools) >= 1
        assert "browser_navigate" in browser_tools

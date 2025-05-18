#!/usr/bin/env python
"""
MCP传输类型测试脚本
用于测试和调试不同类型的MCP传输连接
"""

import logging
import sys
import asyncio
from fastmcp.client import Client, StreamableHttpTransport, SSETransport, StdioTransport


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("test_transport")

async def test_transport(transport, name):
    """测试特定的传输类型"""
    logger.info(f"测试 {name} 传输...")
    try:
        async with Client(transport) as client:
            logger.info(f"成功创建 {name} 客户端连接")
            result = await client.list_tools()
            tool_count = len(result) if result else 0
            logger.info(f"{name} 传输测试成功！获取到 {tool_count} 个工具")
            return True
    except Exception as e:
        logger.error(f"{name} 传输测试失败: {e}")
        return False

async def main():
    """主函数，测试不同类型的传输"""
   
    # 测试本地StreamableHttpTransport（如果有）
    # 注意：确保您有一个运行中的支持streamable-http的本地服务器
    local_streamable_transport = StreamableHttpTransport(url="http://127.0.0.1:8000/mcp")
    await test_transport(local_streamable_transport, "StreamableHttp (本地)")

    
    # 测试SSE传输（本地）
    # 注意：确保您有一个运行中的SSE本地服务器
    transport_sse = SSETransport(url="http://127.0.0.1:8000/sse")
    await test_transport(transport_sse, "SSE")

    transport_stdio = StdioTransport(command="uvx", args=["mcp-server-fetch"])
    await test_transport(transport_stdio, "stdio")

if __name__ == "__main__":
    try:
        asyncio.run(main())
        logger.info("所有测试完成")
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")


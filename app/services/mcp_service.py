from fastmcp import Client
from typing import Dict, Any, List, Optional, Tuple
import json
import os
import tempfile
import logging
from fastapi import Depends
from fastmcp.client import SSETransport, StdioTransport

# 配置日志
logger = logging.getLogger("app.services.mcp")

class MCPService:
    """用于处理外部MCP服务器连接和工具调用的服务"""
    
    async def get_tools_from_config(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从MCP配置中获取工具列表，转换为大模型可用的格式
        
        Args:
            config: MCP配置信息，必须包含mcpServers字段
        
        Returns:
            转换为大模型格式的工具列表
        """
        try:
            # 验证配置是否包含mcpServers
            if "mcpServers" not in config:
                logger.error("配置中缺少mcpServers字段")
                return []
                
            # 获取外部MCP服务器工具
            return await self._get_tools_from_external_servers(config)
        except Exception as e:
            logger.error(f"获取MCP工具时出错: {str(e)}", exc_info=True)
            return []
    
    def _create_mcp_client(self, server_config: Dict[str, Any]) -> Optional[Client]:
        """
        根据服务器配置创建MCP客户端
        
        Args:
            server_config: 服务器配置字典
            
        Returns:
            创建的MCP客户端，如果创建失败则返回None
        """
        try:
            if "url" in server_config:
                # HTTP服务器
                return Client(SSETransport(server_config["url"]))
            elif "command" in server_config:
                # 命令行服务器
                command = server_config["command"]
                args = server_config.get("args", [])
                
                # 设置环境变量
                env = os.environ.copy()
                if "env" in server_config:
                    env.update(server_config["env"])
                
                return Client(StdioTransport(command=command, args=args, env=env))
            else:
                logger.error("无效的服务器配置: 缺少url或command字段")
                return None
        except Exception as e:
            logger.error(f"创建MCP客户端时出错: {str(e)}", exc_info=True)
            return None
    
    async def _create_temp_config_and_client(self, server_name: str, server_config: Dict[str, Any]) -> Tuple[Optional[Client], Optional[str]]:
        """
        创建临时配置文件和MCP客户端
        
        Args:
            server_name: 服务器名称
            server_config: 服务器配置
            
        Returns:
            包含客户端和临时文件路径的元组 (client, temp_file_path)
        """
        # 创建临时配置文件
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_file_path = temp_file.name
                json.dump({server_name: server_config}, temp_file)
            
            # 创建客户端
            client = self._create_mcp_client(server_config)
            return client, temp_file_path
            
        except Exception as e:
            # 如果创建过程中出现错误，尝试清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            logger.error(f"创建临时配置和客户端时出错: {str(e)}", exc_info=True)
            return None, temp_file_path
            
    async def _get_tools_from_external_servers(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从外部MCP服务器配置获取工具列表"""
        all_tools = []
        servers = config.get("mcpServers", {})
        
        for server_name, server_config in servers.items():
            temp_file_path = None
            try:
                logger.info(f"尝试连接外部MCP服务器: {server_name}")
                
                # 创建客户端和临时配置
                client, temp_file_path = await self._create_temp_config_and_client(server_name, server_config)
                
                if client:
                    async with client:
                        # 获取工具列表
                        tools = await client.list_tools()
                        
                        # 转换工具格式
                        server_tools = self._convert_tools_to_openai_format(tools)
                        all_tools.extend(server_tools)
                        
                        logger.info(f"从服务器 {server_name} 获取到 {len(server_tools)} 个工具")
            
            except Exception as e:
                logger.error(f"从服务器 {server_name} 获取工具时出错: {str(e)}", exc_info=True)
            
            finally:
                # 清理临时文件
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.error(f"清理临时文件时出错: {str(e)}")
        
        return all_tools
    
    def _convert_tools_to_openai_format(self, mcp_tools) -> List[Dict[str, Any]]:
        """将MCP工具转换为OpenAI格式"""
        openai_tools = []
        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    async def execute_tool(self, config: Dict[str, Any], tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        执行特定的MCP工具
        
        Args:
            config: MCP配置信息，必须包含mcpServers字段
            tool_name: 要执行的工具名称
            arguments: 工具执行参数
        
        Returns:
            工具执行结果
        """
        try:
            # 验证配置是否包含mcpServers
            if "mcpServers" not in config:
                logger.error("配置中缺少mcpServers字段")
                return "执行工具失败: 配置中缺少mcpServers字段"
                
            # 在外部服务器上执行工具
            return await self._execute_tool_on_external_server(config, tool_name, arguments)
        except Exception as e:
            logger.error(f"执行MCP工具时出错: {str(e)}", exc_info=True)
            return f"执行工具时出错: {str(e)}"
    
    async def _execute_tool_on_external_server(self, config: Dict[str, Any], tool_name: str, arguments: Dict[str, Any]) -> str:
        """在外部服务器上执行工具"""
        servers = config.get("mcpServers", {})
        
        # 遍历所有服务器，尝试找到并执行工具
        for server_name, server_config in servers.items():
            temp_file_path = None
            try:
                logger.info(f"尝试在服务器 {server_name} 上执行工具 {tool_name}, 参数: {arguments}")
                
                # 创建客户端和临时配置
                client, temp_file_path = await self._create_temp_config_and_client(server_name, server_config)
                
                if client:
                    async with client:
                        # 检查工具是否可用
                        tools = await client.list_tools()
                        tool_exists = any(tool.name == tool_name for tool in tools)
                        
                        if tool_exists:
                            # 调用工具
                            result = await client.call_tool(tool_name, arguments)
                            
                            # 处理和格式化结果
                            if result:
                                if hasattr(result[0], 'text'):
                                    return result[0].text
                                else:
                                    return json.dumps(result)
                            return "工具执行完成，但没有返回结果"
            
            except Exception as e:
                logger.error(f"在服务器 {server_name} 上执行工具时出错: {str(e)}", exc_info=True)
            
            finally:
                # 清理临时文件
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.error(f"清理临时文件时出错: {str(e)}")
        
        return f"未找到工具 {tool_name} 或执行失败"

# 依赖注入函数
def get_mcp_service():
    """FastAPI依赖注入，获取MCPService实例"""
    return MCPService() 
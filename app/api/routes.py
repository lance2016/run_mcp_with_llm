from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import json
from openai import OpenAI
import logging
import asyncio
from fastapi.responses import StreamingResponse

from app.services.mcp_service import MCPService, get_mcp_service

# 配置日志
logger = logging.getLogger("app.api")

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str
    function_call: Optional[dict] = None

class ChatRequest(BaseModel):
    messages: List[Message]
    mcp_config: Optional[Dict[str, Any]] = None
    model: str = "doubao-1-5-pro-32k-250115"
    stream: bool = False

class FunctionCall(BaseModel):
    name: str
    arguments: str

class ChatResponse(BaseModel):
    id: str = "chat-response-id"
    object: str = "chat.completion"
    created: int = 0
    model: str = "model-id"
    choices: List[Dict[str, Any]] = Field(default_factory=list)
    usage: Dict[str, int] = Field(default_factory=dict)

@router.post("/chat")
async def chat(request: ChatRequest, mcp_service: MCPService = Depends(get_mcp_service)):
    """与大模型进行对话的接口"""
    try:
        # 获取API密钥
        api_key = os.environ.get("ARK_API_KEY")
        if not api_key and not request.messages:
            # 仅用于测试，如果没有API密钥且没有消息，返回模拟响应
            return {
                "id": "test-response",
                "object": "chat.completion",
                "created": 0,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "这是一个测试响应，因为未设置API密钥。请设置ARK_API_KEY环境变量。"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
        
        # 获取OpenAI客户端 - 确保不传递额外参数
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
        
        # 创建消息列表
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        logger.info(f"准备发送消息到模型，消息数量: {len(messages)}")
        
        # 处理MCP配置
        tools = []
        if request.mcp_config:
            # 验证MCP配置是否包含mcpServers字段
            if "mcpServers" not in request.mcp_config:
                logger.warning("MCP配置中缺少mcpServers字段，无法获取工具列表")
            else:
                # 使用MCP服务解析配置
                tools = await mcp_service.get_tools_from_config(request.mcp_config)
                logger.info(f"获取到MCP工具数量: {len(tools)}")
        
        # 调用大模型
        if request.stream:
            # 流式响应 - 使用FastAPI的StreamingResponse
            async def generate_stream_content():
                try:
                    # 创建流式请求
                    stream = client.chat.completions.create(
                        model=request.model,
                        messages=messages,
                        tools=tools if tools else None,
                        stream=True
                    )
                    
                    # 收集完整的响应用于可能的工具调用
                    full_response = {"choices": [{"message": {"content": "", "tool_calls": []}}]}
                    tool_call_chunks = {}
                    
                    # 收集所有流式数据以确保完整的工具调用参数
                    all_chunks = []
                    try:
                        # 将所有块收集到列表中，以便我们可以完整处理工具调用
                        for chunk in stream:
                            all_chunks.append(chunk)
                            # 将数据块发送到客户端
                            yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                            await asyncio.sleep(0.01)  # 让出控制权，确保流式处理正常
                    except Exception as e:
                        logger.error(f"处理流式数据时出错: {str(e)}", exc_info=True)
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    
                    # 整理工具调用数据
                    has_tool_calls = False
                    function_tools = {}  # 使用索引作为键存储工具调用信息
                    
                    for chunk in all_chunks:
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            
                            # 处理内容
                            if hasattr(delta, 'content') and delta.content:
                                full_response["choices"][0]["message"]["content"] += delta.content
                            
                            # 处理工具调用
                            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                has_tool_calls = True
                                for tc in delta.tool_calls:
                                    # 记录每个工具调用块以便调试
                                    logger.debug(f"工具调用块: {tc.model_dump()}")
                                    
                                    # 获取工具调用索引
                                    idx = tc.index
                                    
                                    # 如果是新的工具调用索引，初始化
                                    if idx not in function_tools:
                                        function_tools[idx] = {"name": "", "arguments": ""}
                                    
                                    # 收集函数名称
                                    if hasattr(tc.function, 'name') and tc.function.name is not None:
                                        function_tools[idx]["name"] += tc.function.name
                                    
                                    # 收集函数参数
                                    if hasattr(tc.function, 'arguments') and tc.function.arguments is not None:
                                        function_tools[idx]["arguments"] += tc.function.arguments
                    
                    # 检查是否有工具调用，并确保参数是完整的
                    if has_tool_calls and function_tools:
                        # 记录所有收集到的工具调用
                        logger.info(f"流式响应中检测到工具调用，数量: {len(function_tools)}")
                        logger.info(f"收集到的所有工具调用: {function_tools}")
                        
                        # 取第一个工具调用
                        first_idx = list(function_tools.keys())[0]
                        function_call = function_tools[first_idx]
                        logger.info(f"将要执行的工具调用: {function_call}")
                        
                        try:
                            # 检查工具名称是否存在
                            if not function_call.get("name"):
                                error_msg = "工具调用缺少名称"
                                logger.error(error_msg)
                                yield f"data: {json.dumps({'tool_execution_error': True, 'error': error_msg})}\n\n"
                                yield "data: [DONE]\n\n"
                                return
                            
                            # 安全解析参数
                            tool_arguments = {}
                            arguments_str = function_call.get("arguments", "").strip()
                            
                            logger.info(f"原始参数字符串: '{arguments_str}'")
                            
                            # 尝试各种方式解析参数
                            if arguments_str:
                                try:
                                    # 首先尝试作为JSON对象解析
                                    if arguments_str.startswith("{") and arguments_str.endswith("}"):
                                        tool_arguments = json.loads(arguments_str)
                                    # 尝试作为单个数字或字符串参数
                                    elif arguments_str.isdigit():
                                        # 对于天气查询，假设单个数字可能是城市ID
                                        tool_arguments = {"city_id": int(arguments_str)}
                                    else:
                                        # 对于天气查询，假设单个字符串可能是城市名
                                        tool_arguments = {"city": arguments_str}
                                    
                                    logger.info(f"解析后的工具参数: {tool_arguments}")
                                except json.JSONDecodeError as e:
                                    logger.warning(f"JSON参数解析失败，尝试其他解析方式: {e}")
                                    # 尝试将参数视为城市名
                                    tool_arguments = {"city": arguments_str}
                            
                            # 使用解析后的参数执行工具
                            logger.info(f"执行工具: {function_call['name']} 参数: {tool_arguments}")
                            
                            # 构建标准化的工具调用对象
                            tool_call_id = f"call_{first_idx}"
                            standard_tool_call = {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": function_call["name"],
                                    "arguments": json.dumps(tool_arguments) if tool_arguments else "{}"
                                }
                            }
                            
                            # 执行工具调用
                            tool_result = await mcp_service.execute_tool(
                                request.mcp_config,
                                function_call["name"],
                                tool_arguments
                            )
                            
                            # 将助手的工具调用添加到消息历史
                            messages.append({
                                "role": "assistant",
                                "content": full_response["choices"][0]["message"]["content"],
                                "tool_calls": [standard_tool_call]
                            })
                            
                            # 添加工具响应
                            messages.append({
                                "role": "tool",
                                "name": function_call["name"],
                                "content": tool_result,
                                "tool_call_id": tool_call_id
                            })
                            
                            # 通知前端工具执行完成，包含工具调用参数和结果
                            yield f"data: {json.dumps({
                                'tool_execution_complete': True, 
                                'tool_name': function_call['name'],
                                'tool_arguments': tool_arguments,
                                'tool_result': tool_result
                            })}\n\n"
                            
                            logger.info("工具执行成功，继续流式响应...")
                            
                            # 使用更新后的消息再次调用模型获取最终回复
                            try:
                                final_stream = client.chat.completions.create(
                                    model=request.model,
                                    messages=messages,
                                    tools=tools if tools else None,
                                    stream=True
                                )
                                
                                # 继续流式发送最终响应
                                for chunk in final_stream:
                                    yield f"data: {json.dumps(chunk.model_dump())}\n\n"
                                    await asyncio.sleep(0.01)  # 让出控制权，确保流式处理正常
                            except Exception as e:
                                logger.error(f"生成最终响应时出错: {str(e)}", exc_info=True)
                                yield f"data: {json.dumps({'error': f'生成最终响应时出错: {str(e)}'})}\n\n"
                        
                        except Exception as e:
                            logger.error(f"流式响应中执行工具时出错: {str(e)}", exc_info=True)
                            # 通知前端工具执行错误
                            yield f"data: {json.dumps({'tool_execution_error': True, 'error': str(e)})}\n\n"
                    
                    yield "data: [DONE]\n\n"
                
                except Exception as e:
                    logger.error(f"生成流式响应时出错: {str(e)}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream_content(),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            completion = client.chat.completions.create(
                model=request.model,
                messages=messages,
                tools=tools if tools else None,
                stream=False
            )
            logger.info(f"completion: {completion}")
            logger.info(f"completion.choices: {completion.choices}")
            logger.info(f"completion.choices[0].message: {completion.choices[0].message}")
            logger.info(f"completion.choices[0].message.tool_calls: {completion.choices[0].message.tool_calls}")
            # 检查是否有工具调用
            if completion.choices and hasattr(completion.choices[0].message, 'tool_calls') and completion.choices[0].message.tool_calls:
                function_call = completion.choices[0].message.tool_calls[0].function
                logger.info(f"检测到函数调用: {function_call.name}")
                
                # 使用MCP服务执行工具调用
                tool_result = await mcp_service.execute_tool(
                    request.mcp_config,
                    function_call.name, 
                    json.loads(function_call.arguments)
                )
                
                # 先添加助手的工具调用消息
                tool_call_id = f"call_{function_call.name}"
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": function_call.name,
                                "arguments": function_call.arguments
                            }
                        }
                    ]
                })
                
                # 然后添加工具执行结果消息
                messages.append({
                    "role": "tool",  # 确保使用API支持的role值
                    "name": function_call.name,
                    "content": tool_result,
                    "tool_call_id": tool_call_id  # 添加必要的tool_call_id参数
                })
                
                logger.info(f"函数执行完成，结果长度: {len(tool_result)}")
                logger.info(f"messages: {messages}")
                # 再次调用大模型，将工具结果传递给它
                completion = client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    tools=tools if tools else None,
                    stream=False
                )
            
            # 将响应转换为字典并返回
            try:
                return completion.model_dump()
            except AttributeError:
                # 旧版本API可能没有model_dump方法
                return completion.dict() if hasattr(completion, 'dict') else completion
    
    except Exception as e:
        logger.error(f"调用大模型时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"调用大模型时出错: {str(e)}")

@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"} 
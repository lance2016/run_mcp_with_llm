#!/bin/bash
# 启动天气MCP服务器

# 确保依赖已安装
echo "检查依赖..."
pip install fastmcp uvicorn requests

# 启动天气服务
echo "启动天气MCP服务器..."
python weather_service.py 
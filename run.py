#!/usr/bin/env python
import uvicorn
import os
import argparse
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("run")

def main():
    """主函数，启动FastAPI应用"""
    parser = argparse.ArgumentParser(description='启动外部MCP服务器大模型演示')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听主机 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='监听端口 (默认: 8080)')
    parser.add_argument('--api-key', type=str, help='设置ARK API密钥')
    args = parser.parse_args()
    
    # 设置API密钥环境变量
    if args.api_key:
        os.environ['ARK_API_KEY'] = args.api_key
        logger.info("已设置API密钥")
    else:
        if 'ARK_API_KEY' not in os.environ:
            logger.warning("未设置ARK_API_KEY环境变量，应用将以测试模式运行")
    
    # 启动服务器
    logger.info(f"启动服务器 http://{args.host}:{args.port}")
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=True
    )

if __name__ == "__main__":
    main() 
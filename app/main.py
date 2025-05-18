from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.api.routes import router as api_router

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("app")

# 异常处理中间件
class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"请求处理异常: {str(e)}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"detail": f"服务器内部错误: {str(e)}"}
            )

app = FastAPI(title="FastMCP 大模型应用")

# 添加中间件
app.add_middleware(ExceptionMiddleware)

# 添加CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="app/templates")

# 包含API路由
app.include_router(api_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """返回前端页面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "ok"}

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": f"未找到请求的路径: {request.url.path}"}
    )

@app.exception_handler(500)
async def server_error_exception_handler(request: Request, exc):
    logger.error(f"服务器错误: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误"}
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求的中间件"""
    logger.info(f"请求路径: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"响应状态: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}")
        raise

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8888, reload=True) 
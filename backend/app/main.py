"""FastAPI 入口：CORS + 路由挂载。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import platform

app = FastAPI(title="Growth Intelligence Platform", version="0.1.0")

# 跨域：FRONTEND_ORIGIN=*（默认）→ 放行所有来源但不带凭据；
# 生产配置为具体前端域名（如 https://xxx.vercel.app）→ 白名单 + 允许凭据。
_cors_origins = (
    ["*"]
    if settings.frontend_origin == "*"
    else [
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=settings.frontend_origin != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(platform.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

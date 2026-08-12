"""应用配置：环境变量。开发默认 SQLite，生产用 DATABASE_URL(Neon Postgres)。"""
import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_settings():
    class Settings:
        # 数据库：生产部署时用 Neon Postgres 的 DATABASE_URL 覆盖
        database_url: str = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'growth.db')}",
        )
        # DeepSeek 报告服务
        deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        deepseek_base_url: str = os.getenv(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )
        deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        # 前端跨域：本地默认放行所有来源（开发期方便）；生产部署填 Vercel 域名，
        # 如 FRONTEND_ORIGIN=https://growth-intel.vercel.app
        frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "*")
        # 数据范围（seed 用）
        start_date: str = os.getenv("SEED_START_DATE", "2026-02-01")
        # 观察期结束在整月，保证 K 因子 / 流失等按「完整月」口径口径（无残缺月）
        end_date: str = os.getenv("SEED_END_DATE", "2026-07-31")
        n_users: int = int(os.getenv("SEED_N_USERS", "15000"))

    return Settings()


settings = get_settings()

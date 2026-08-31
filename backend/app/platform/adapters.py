from __future__ import annotations

import csv
import re
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import duckdb


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")


def quote_identifier(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"不安全的标识符：{value}")
    return '"' + value.replace('"', '""') + '"'


class Adapter(ABC):
    def __init__(self, source: dict[str, Any], base: Path):
        self.source, self.base = source, base

    @abstractmethod
    def test(self) -> dict: ...

    @abstractmethod
    def schema(self) -> list[dict]: ...

    @abstractmethod
    def preview(self, limit: int = 20) -> list[dict]: ...

    @abstractmethod
    def relation_sql(self) -> str: ...


class FileAdapter(Adapter):
    kind: str

    @property
    def path(self) -> Path:
        raw = Path(self.source["path"])
        return raw if raw.is_absolute() else (self.base / raw).resolve()

    def relation_sql(self) -> str:
        safe = self.path.as_posix().replace("'", "''")
        return f"read_{self.kind}('{safe}')" if self.kind == "parquet" else f"read_csv_auto('{safe}', header=true)"

    def _connection(self):
        if not self.path.exists():
            raise FileNotFoundError(str(self.path))
        return duckdb.connect()

    def test(self) -> dict:
        con = self._connection()
        rows = con.execute(f"SELECT count(*) FROM {self.relation_sql()}").fetchone()[0]
        con.close()
        return {"ok": True, "type": self.kind, "rows": rows, "path": str(self.path)}

    def schema(self) -> list[dict]:
        con = self._connection(); frame = con.execute(f"DESCRIBE SELECT * FROM {self.relation_sql()}").fetchdf(); con.close()
        return frame[["column_name", "column_type", "null"]].to_dict("records")

    def preview(self, limit: int = 20) -> list[dict]:
        con = self._connection(); frame = con.execute(f"SELECT * FROM {self.relation_sql()} LIMIT ?", [min(max(limit, 1), 100)]).fetchdf(); con.close()
        return frame.astype(object).where(frame.notna(), None).to_dict("records")


class CsvAdapter(FileAdapter): kind = "csv"
class ParquetAdapter(FileAdapter): kind = "parquet"


class SQLiteAdapter(Adapter):
    @property
    def path(self) -> Path:
        raw = Path(self.source["path"]); return raw if raw.is_absolute() else (self.base / raw).resolve()

    @property
    def table(self) -> str: return self.source["table"]

    def relation_sql(self) -> str:
        safe = self.path.as_posix().replace("'", "''")
        return f"sqlite_scan('{safe}', {quote_identifier(self.table)})"

    def test(self) -> dict:
        with sqlite3.connect(self.path) as con:
            con.execute(f"SELECT 1 FROM {quote_identifier(self.table)} LIMIT 1")
        return {"ok": True, "type": "sqlite", "table": self.table}

    def schema(self) -> list[dict]:
        with sqlite3.connect(self.path) as con:
            rows = con.execute(f"PRAGMA table_info({quote_identifier(self.table)})").fetchall()
        return [{"column_name": r[1], "column_type": r[2], "null": not bool(r[3])} for r in rows]

    def preview(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute(f"SELECT * FROM {quote_identifier(self.table)} LIMIT ?", [min(max(limit,1),100)])]


class PostgreSQLAdapter(Adapter):
    def relation_sql(self) -> str:
        dsn = self.source["dsn_env"]
        table = quote_identifier(self.source["table"])
        return f"postgres_scan(current_setting('{dsn}'), 'public', {table})"

    def _connect(self):
        import os, psycopg2
        dsn = os.getenv(self.source.get("dsn_env", "POSTGRES_URL"))
        if not dsn: raise ValueError("PostgreSQL 连接环境变量未设置")
        return psycopg2.connect(dsn, connect_timeout=5)

    def test(self) -> dict:
        with self._connect() as con: con.cursor().execute("SELECT 1")
        return {"ok": True, "type": "postgresql"}

    def schema(self) -> list[dict]:
        with self._connect() as con:
            cur=con.cursor(); cur.execute("SELECT column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",[self.source["table"]]); rows=cur.fetchall()
        return [{"column_name":r[0],"column_type":r[1],"null":r[2]=="YES"} for r in rows]

    def preview(self, limit: int = 20) -> list[dict]:
        with self._connect() as con:
            cur=con.cursor(); cur.execute(f"SELECT * FROM {quote_identifier(self.source['table'])} LIMIT %s",[min(max(limit,1),100)]); names=[d[0] for d in cur.description]; return [dict(zip(names,row)) for row in cur.fetchall()]


def create_adapter(source: dict[str, Any], base: Path) -> Adapter:
    adapters = {"csv": CsvAdapter, "parquet": ParquetAdapter, "sqlite": SQLiteAdapter, "postgresql": PostgreSQLAdapter}
    try: return adapters[source["type"]](source, base)
    except KeyError as exc: raise ValueError(f"不支持的数据源：{source.get('type')}") from exc


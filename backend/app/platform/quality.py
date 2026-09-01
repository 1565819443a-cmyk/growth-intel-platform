from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import duckdb

from .adapters import quote_identifier
from .registry import DatasetRegistry


def run_quality(dataset_id:str,registry:DatasetRegistry|None=None)->dict:
    registry=registry or DatasetRegistry(); config=registry.load(dataset_id); adapter=registry.adapter(dataset_id); relation=adapter.relation_sql(); con=duckdb.connect(); checks=[]
    for rule in config.get("quality_rules",[]):
        field=quote_identifier(rule["field"]); kind=rule["type"]
        if kind=="non_null": sql=f"SELECT count(*) FROM {relation} WHERE {field} IS NULL"
        elif kind=="conditional_non_null": sql=f"SELECT count(*) FROM {relation} WHERE ({rule['when']}) AND {field} IS NULL"
        elif kind=="range":
            clauses=[]; params=[]
            if "min" in rule: clauses.append(f"try_cast({field} AS DOUBLE) < ?"); params.append(rule["min"])
            if "max" in rule: clauses.append(f"try_cast({field} AS DOUBLE) > ?"); params.append(rule["max"])
            sql=f"SELECT count(*) FROM {relation} WHERE "+" OR ".join(clauses)
        elif kind=="accepted_values":
            values=rule["values"]; sql=f"SELECT count(*) FROM {relation} WHERE {field} IS NULL OR {field} NOT IN ({','.join('?' for _ in values)})"; params=values
        elif kind=="unique": sql=f"SELECT count(*)-count(DISTINCT {field}) FROM {relation}"
        else: raise ValueError(f"不支持的质量规则：{kind}")
        failures=int(con.execute(sql,locals().get("params",[])).fetchone()[0] or 0)
        severity = rule.get("severity", "error")
        status="passed" if failures==0 else ("warning" if severity in {"warn", "warning"} else "failed")
        checks.append({"id":rule["id"],"type":kind,"field":rule["field"],"severity":severity,"status":status,"failures":failures})
        params=[]
    con.close(); return {"dataset_id":dataset_id,"checked_at":datetime.now(timezone.utc).isoformat(),"rules":len(checks),"passed":sum(x["status"]=="passed" for x in checks),"warnings":sum(x["status"]=="warning" for x in checks),"failed":sum(x["status"]=="failed" for x in checks),"checks":checks}


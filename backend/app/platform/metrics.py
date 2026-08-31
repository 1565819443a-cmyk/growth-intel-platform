from __future__ import annotations

import re
from typing import Any

import duckdb

from .adapters import quote_identifier
from .registry import DatasetRegistry


SAFE_EXPRESSION = re.compile(r"^[A-Za-z0-9_\s(),'*=.< >+\-/]+$")


class MetricEngine:
    def __init__(self, registry: DatasetRegistry | None = None): self.registry=registry or DatasetRegistry()

    @staticmethod
    def _configured_expression(metric: dict[str, Any]) -> str:
        agg=metric["aggregation"]
        if agg=="count": expr="count(*)"
        elif agg=="distinct_count": expr=f"count(distinct {quote_identifier(metric['field'])})"
        elif agg=="sum": expr=f"sum({quote_identifier(metric['field'])})"
        elif agg=="average": expr=f"avg({quote_identifier(metric['field'])})"
        elif agg=="ratio":
            numerator,denominator=metric["numerator"],metric["denominator"]
            if not SAFE_EXPRESSION.fullmatch(numerator) or not SAFE_EXPRESSION.fullmatch(denominator): raise ValueError("ratio 表达式包含非法字符")
            expr=f"({numerator}) / nullif(({denominator}),0)"
        elif agg=="derived":
            expr=metric["expression"]
            if not SAFE_EXPRESSION.fullmatch(expr): raise ValueError("派生指标表达式包含非法字符")
        else: raise ValueError(f"不支持的聚合：{agg}")
        filter_sql=metric.get("filter")
        if filter_sql:
            if not SAFE_EXPRESSION.fullmatch(filter_sql): raise ValueError("指标过滤表达式非法")
            if agg=="ratio": raise ValueError("ratio 指标应分别在分子和分母中定义过滤")
            expr=f"{expr} FILTER (WHERE {filter_sql})"
        return expr

    def query(self,dataset_id:str,metric_id:str,dimension:str|None=None,time_grain:str|None=None,filters:dict[str,Any]|None=None,calculation:str="raw")->dict:
        config=self.registry.load(dataset_id); metrics=config["metrics"]
        if metric_id not in metrics: raise KeyError(f"指标不存在：{metric_id}")
        metric=metrics[metric_id]; adapter=self.registry.adapter(dataset_id); schema={x["column_name"] for x in adapter.schema()}
        expr=self._configured_expression(metric)
        selects=[]; groups=[]; params=[]; where=[]
        if dimension:
            if dimension not in config.get("dimensions",[]) or dimension not in schema: raise ValueError("维度未获授权或不存在")
            selects.append(quote_identifier(dimension)); groups.append(quote_identifier(dimension))
        if time_grain:
            if time_grain not in {"day","week","month"}: raise ValueError("时间粒度仅支持 day/week/month")
            time_field=config["mappings"].get("time")
            if not isinstance(time_field,str) or time_field not in schema: raise ValueError("数据集缺少可用时间字段")
            time_expr=f"date_trunc('{time_grain}', try_cast({quote_identifier(time_field)} AS TIMESTAMP))"
            selects.append(f"{time_expr} AS period"); groups.append(time_expr)
        for key,value in (filters or {}).items():
            if key not in config.get("dimensions",[]) or key not in schema: raise ValueError(f"过滤字段未获授权：{key}")
            where.append(f"{quote_identifier(key)} = ?"); params.append(value)
        select_sql=(", ".join(selects)+", ") if selects else ""
        sql=f"SELECT {select_sql}{expr} AS value FROM {adapter.relation_sql()}"
        if where: sql+=" WHERE "+" AND ".join(where)
        if groups: sql+=" GROUP BY "+",".join(groups)+" ORDER BY "+",".join(groups)
        if calculation not in {"raw","cumulative","period_change"}: raise ValueError("calculation 仅支持 raw/cumulative/period_change")
        if calculation!="raw":
            if not time_grain: raise ValueError("累计或环比需要 time_grain")
            dims=[quote_identifier(dimension)] if dimension else []
            partition=f"PARTITION BY {dims[0]} " if dims else ""
            keys=", ".join(dims+["period"])
            if calculation=="cumulative": sql=f"SELECT {keys}, sum(\"value\") OVER ({partition}ORDER BY period) AS \"value\" FROM ({sql}) base ORDER BY {keys}"
            else: sql=f"SELECT {keys}, \"value\"/nullif(lag(\"value\") OVER ({partition}ORDER BY period),0)-1 AS \"value\" FROM ({sql}) base ORDER BY {keys}"
        con=duckdb.connect(); frame=con.execute(sql,params).fetchdf(); con.close()
        rows=frame.astype(object).where(frame.notna(),None).to_dict("records")
        return {"dataset_id":dataset_id,"metric_id":metric_id,"metric_name":metric.get("name"),"owner":metric.get("owner"),"version":metric.get("version"),"dimension":dimension,"time_grain":time_grain,"calculation":calculation,"rows":rows,"generated_sql":sql}

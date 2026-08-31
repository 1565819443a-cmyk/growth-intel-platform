from __future__ import annotations

import duckdb

from .adapters import quote_identifier
from .registry import DatasetRegistry, capabilities


def funnel(dataset_id:str,registry:DatasetRegistry|None=None)->dict:
    registry=registry or DatasetRegistry(); config=registry.load(dataset_id); caps=capabilities(config)
    if not caps["funnel"]["enabled"]: raise ValueError(caps["funnel"]["reason"])
    m=config["mappings"]; user=quote_identifier(m["user_id"]); event=quote_identifier(m["event_type"]); time=quote_identifier(m["time"]); steps=config["funnel_steps"]; adapter=registry.adapter(dataset_id)
    time_cols=",".join(f"min(try_cast({time} AS TIMESTAMP)) filter(where {event}=?) t{i}" for i in range(len(steps)))
    con=duckdb.connect(); rows=con.execute(f"WITH s AS (SELECT {user},{time_cols} FROM {adapter.relation_sql()} GROUP BY {user}) SELECT {','.join(f'count(*) filter(where t{i} is not null'+''.join(f' and t{j}>=t{j-1}' for j in range(1,i+1))+f') n{i}' for i in range(len(steps)))} FROM s",steps).fetchone(); con.close()
    return {"dataset_id":dataset_id,"steps":[{"step":step,"users":int(rows[i])} for i,step in enumerate(steps)]}


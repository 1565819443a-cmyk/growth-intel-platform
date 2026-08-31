from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..platform.analysis import funnel
from ..platform.metrics import MetricEngine
from ..platform.quality import run_quality
from ..platform.registry import DatasetRegistry, capabilities

router=APIRouter(prefix="/api/v1",tags=["platform"])
registry=DatasetRegistry(); engine=MetricEngine(registry)


def guarded(call):
    try: return call()
    except KeyError as exc: raise HTTPException(404,str(exc)) from exc
    except FileNotFoundError as exc: raise HTTPException(503,f"数据文件未导入：{exc}") from exc
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc


@router.get("/datasets")
def datasets(): return registry.list()

@router.get("/datasets/{dataset_id}")
def dataset(dataset_id:str):
    def detail():
        config=registry.load(dataset_id)
        return {**config,"source_type":config["source"]["type"],"available":registry.adapter(dataset_id).test()["ok"],"capabilities":capabilities(config)}
    return guarded(detail)

@router.get("/datasets/{dataset_id}/connection")
def connection(dataset_id:str): return guarded(lambda:registry.adapter(dataset_id).test())

@router.get("/datasets/{dataset_id}/schema")
def schema(dataset_id:str): return guarded(lambda:registry.adapter(dataset_id).schema())

@router.get("/datasets/{dataset_id}/preview")
def preview(dataset_id:str,limit:int=Query(20,ge=1,le=100)): return guarded(lambda:registry.adapter(dataset_id).preview(limit))

@router.get("/datasets/{dataset_id}/metrics")
def metrics(dataset_id:str): return guarded(lambda:registry.load(dataset_id)["metrics"])

@router.get("/datasets/{dataset_id}/metrics/{metric_id}")
def metric(dataset_id:str,metric_id:str,dimension:str|None=None,time_grain:str|None=None,calculation:str="raw"): return guarded(lambda:engine.query(dataset_id,metric_id,dimension,time_grain,calculation=calculation))

@router.get("/datasets/{dataset_id}/quality")
def quality(dataset_id:str): return guarded(lambda:run_quality(dataset_id,registry))

@router.get("/datasets/{dataset_id}/lineage")
def lineage(dataset_id:str): return guarded(lambda:registry.load(dataset_id).get("lineage",{}))

@router.get("/datasets/{dataset_id}/funnel")
def funnel_api(dataset_id:str): return guarded(lambda:funnel(dataset_id,registry))

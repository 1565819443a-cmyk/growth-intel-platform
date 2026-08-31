from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .adapters import create_adapter


REQUIRED = {"id", "name", "source", "mappings", "metrics"}


class DatasetRegistry:
    def __init__(self, backend_root: Path | None = None):
        self.root = (backend_root or Path(__file__).resolve().parents[2]).resolve()
        self.config_dir = self.root / "configs/datasets"

    def load(self, dataset_id: str) -> dict[str, Any]:
        path = self.config_dir / f"{dataset_id}.yaml"
        if not path.exists(): raise KeyError(f"数据集不存在：{dataset_id}")
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        missing = REQUIRED - config.keys()
        if missing: raise ValueError(f"数据集配置缺少：{sorted(missing)}")
        if config["id"] != dataset_id: raise ValueError("文件名与数据集 id 不一致")
        return config

    def list(self) -> list[dict[str, Any]]:
        result=[]
        for path in sorted(self.config_dir.glob("*.yaml")):
            config=self.load(path.stem); adapter=create_adapter(config["source"],self.root)
            try: connection=adapter.test(); available=True; error=None
            except Exception as exc: connection=None; available=False; error=str(exc)
            result.append({"id":config["id"],"name":config["name"],"description":config.get("description"),"version":config.get("version"),"status":config.get("status","active"),"source_type":config["source"]["type"],"available":available,"connection":connection,"error":error,"capabilities":capabilities(config)})
        return result

    def adapter(self, dataset_id: str):
        config=self.load(dataset_id); return create_adapter(config["source"],self.root)


def capabilities(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    m=config.get("mappings",{}); metrics=config.get("metrics",{}); rules=config.get("quality_rules",[])
    tests={
      "overview": (bool(metrics), "需要至少一个指标"),
      "trend": ("time" in m, "需要时间字段"),
      "funnel": (all(x in m for x in ["user_id","event_type","time"]) and bool(config.get("funnel_steps")), "需要用户、事件、时间和漏斗步骤"),
      "retention": (all(x in m for x in ["user_id","time"]), "需要用户与时间序列"),
      "rfm": (all(x in m for x in ["user_id","time","amount","order_id"]), "需要用户、时间、金额和订单"),
      "channel": ("channel" in m, "需要渠道字段"),
      "campaign": ("campaign" in m, "需要活动字段"),
      "region": ("region" in m, "需要地区字段"),
      "institution": ("institution_id" in m, "需要机构字段"),
      "quality": (bool(rules), "需要质量规则"),
      "gmv": ("amount" in m and any(k in metrics for k in ["gmv","revenue","originated_amount"]), "需要金额映射和金额指标"),
    }
    return {name:{"enabled":ok,"reason":None if ok else reason} for name,(ok,reason) in tests.items()}


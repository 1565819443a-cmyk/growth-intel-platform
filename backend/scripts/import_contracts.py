from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def copy_contract(source: str, target: Path) -> None:
    path=Path(source).expanduser().resolve()
    if not path.exists(): raise FileNotFoundError(path)
    target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
    print(f"imported {path} -> {target}")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="导入领域项目标准 Parquet 契约")
    parser.add_argument("--ga4",help="ga4_events.parquet 路径")
    parser.add_argument("--hmda",help="hmda_applications.parquet 路径")
    args=parser.parse_args(); root=Path(__file__).resolve().parents[1]/"data/imports"
    if args.ga4: copy_contract(args.ga4,root/"ga4_events.parquet")
    if args.hmda: copy_contract(args.hmda,root/"hmda_applications.parquet")
    if not args.ga4 and not args.hmda: parser.error("至少提供 --ga4 或 --hmda")


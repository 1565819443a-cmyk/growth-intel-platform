from pathlib import Path

import duckdb


def pytest_sessionstart(session):
    root=Path(__file__).resolve().parents[1]
    imports=root/"data/imports"; imports.mkdir(parents=True,exist_ok=True)
    for name in ["ga4_events","hmda_applications"]:
        target=imports/f"{name}.parquet"
        if target.exists(): continue
        source=(root/"tests/fixtures"/f"{name}.csv").as_posix().replace("'","''")
        output=target.as_posix().replace("'","''")
        con=duckdb.connect(); con.execute(f"COPY (SELECT * FROM read_csv_auto('{source}',header=true)) TO '{output}' (FORMAT PARQUET)"); con.close()


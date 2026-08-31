import sqlite3

from app.platform.adapters import SQLiteAdapter, create_adapter, quote_identifier
from app.platform.registry import DatasetRegistry


def test_csv_schema_and_preview():
    registry=DatasetRegistry(); adapter=registry.adapter("demo_ecommerce")
    assert adapter.test()["rows"]==20
    assert "user_id" in {c["column_name"] for c in adapter.schema()}
    assert len(adapter.preview(3))==3


def test_sqlite_adapter(tmp_path):
    path=tmp_path/"source.db"
    with sqlite3.connect(path) as con:
        con.execute("create table records(id integer,name text)"); con.execute("insert into records values(1,'a')")
    adapter=SQLiteAdapter({"type":"sqlite","path":str(path),"table":"records"},tmp_path)
    assert adapter.test()["ok"]
    assert adapter.preview()==[{"id":1,"name":"a"}]


def test_identifier_injection_is_rejected():
    try: quote_identifier("users; drop table x")
    except ValueError: pass
    else: raise AssertionError("unsafe identifier accepted")


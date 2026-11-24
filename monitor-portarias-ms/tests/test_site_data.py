import json

from site_data import write_site_data


def test_site_data_contains_timestamp_and_public_records(tmp_path):
    path = tmp_path / "site" / "data.json"
    records = [{"title": "Portaria pública", "relevance": "alta"}]

    write_site_data(records, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["records"] == records
    assert payload["updated_at"]

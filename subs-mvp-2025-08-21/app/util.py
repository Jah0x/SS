from uuid import UUID
import json

try:
    import orjson as _json
    def json_loads(b):
        return _json.loads(b)
except Exception:
    def json_loads(b):
        return json.loads(b)

def parse_uuid_list_from_clients_json(payload):
    data = json_loads(payload)
    out = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                try:
                    out.append(UUID(str(item["id"])))
                except Exception:
                    continue
    elif isinstance(data, dict):
        clients = data.get("clients", [])
        for item in clients:
            if isinstance(item, dict) and item.get("id"):
                try:
                    out.append(UUID(str(item["id"])))
                except Exception:
                    continue
    return out

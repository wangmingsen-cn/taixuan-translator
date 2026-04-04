import httpx, json

r = httpx.get("http://127.0.0.1:8000/api/engines")
d = r.json()
print(f"Status: {r.status_code}")
print(f"Total: {d['data']['total_count']} engines, {d['data']['configured_count']} available")
print(f"Default: {d['data']['default_engine']}")
print()
for e in d['data']['engines']:
    cfg = "OK" if e['configured'] else "--"
    avl = "UP" if e['available'] else "  "
    print(f"  [{cfg}][{avl}] P{e['priority']} {e['name']:10} {e['model']:30} {e['note'][:40]}")

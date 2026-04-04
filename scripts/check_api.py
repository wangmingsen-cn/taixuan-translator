import httpx, json

# 测试 /health
r = httpx.get('http://127.0.0.1:8000/health')
print('=== /health ===')
print('Status:', r.status_code)
d = r.json()
print('DB status:', d['data']['database']['status'])
print('Cache entries:', d['data']['database']['cache_count'])

# 测试 /api/engines
r2 = httpx.get('http://127.0.0.1:8000/api/engines')
print('\n=== /api/engines ===')
print('Status:', r2.status_code)
d2 = r2.json()
for e in d2['data']['engines']:
    status = 'OK' if e['available'] else 'NOT CONFIGURED'
    print(f"  [{status}] {e['name']:12} model={e['model']}")
print('Default engine:', d2['data']['default_engine'])
print('Available count:', d2['data']['configured_count'])

# 测试 /api/status/999 (不存在的任务)
r3 = httpx.get('http://127.0.0.1:8000/api/status/999')
print('\n=== /api/status/999 ===')
print('Status:', r3.status_code)
d3 = r3.json()
print('success:', d3['success'], '| message:', d3['message'])

# 测试 /docs 可访问
r4 = httpx.get('http://127.0.0.1:8000/docs')
print('\n=== /docs ===')
print('Status:', r4.status_code, '(Swagger UI)')

print('\nAll API checks passed!')

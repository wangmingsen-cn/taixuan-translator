"""
端到端集成测试：上传 → 状态查询 → 模拟翻译 → 导出Word
"""
import httpx, json
from pathlib import Path

BASE = "http://127.0.0.1:8000"

# Step 1: 上传文件
print("=" * 50)
print("Step 1: POST /api/upload")
test_content = "Deep Learning Survey\n\nIn recent years, deep learning has revolutionized AI.\n\nTransformer architectures dominate NLP tasks."
files = {'file': ('e2e_test.txt', test_content.encode('utf-8'), 'text/plain')}
r = httpx.post(f"{BASE}/api/upload", files=files)
d = r.json()
assert d['success'], f"Upload failed: {d['message']}"
task_id = d['data']['task_id']
segments = d['data']['segments']
print(f"  task_id={task_id}, segments={len(segments)}")

# Step 2: 查询状态
print("\nStep 2: GET /api/status/{task_id}")
r2 = httpx.get(f"{BASE}/api/status/{task_id}")
d2 = r2.json()
assert d2['success'], f"Status failed: {d2['message']}"
print(f"  status={d2['data']['status']}, progress={d2['data']['progress']}%")

# Step 3: 查询引擎列表
print("\nStep 3: GET /api/engines")
r3 = httpx.get(f"{BASE}/api/engines")
d3 = r3.json()
assert d3['success']
for e in d3['data']['engines']:
    icon = "OK" if e['available'] else "--"
    print(f"  {icon} {e['name']:12} {e['model']}")

# Step 4: 导出Word（模拟翻译结果）
print("\nStep 4: POST /api/export/docx")
mock_translations = [
    {"index": s['index'], "source_text": s['text'],
     "translated_text": f"[译文] {s['text']}", "type": s['type'], "page": s['page']}
    for s in segments
]
export_payload = {
    "task_id": task_id,
    "file_name": "e2e_test.txt",
    "segments": mock_translations,
    "bilingual_mode": "interleaved",
    "target_language": "zh-Hans",
    "apply_publication_std": True,
}
r4 = httpx.post(f"{BASE}/api/export/docx", json=export_payload, timeout=30)
d4 = r4.json()
assert d4['success'], f"Export failed: {d4['message']}"
print(f"  file_name={d4['data']['file_name']}")
print(f"  file_size={d4['data']['file_size_kb']}KB")
print(f"  download_url={d4['data']['download_url']}")

# Step 5: 下载文件
print("\nStep 5: GET /api/downloads/{filename}")
fname = d4['data']['file_name']
r5 = httpx.get(f"{BASE}/api/downloads/{fname}")
assert r5.status_code == 200, f"Download failed: {r5.status_code}"
print(f"  Downloaded {len(r5.content)} bytes")
print(f"  Content-Type: {r5.headers.get('content-type')}")

print("\n" + "=" * 50)
print("ALL E2E TESTS PASSED!")
print("=" * 50)

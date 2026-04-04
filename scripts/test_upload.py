import httpx, json, io

# 构造测试TXT文件
test_content = """Deep Learning Survey

In recent years, deep learning has revolutionized the field of artificial intelligence.

Convolutional Neural Networks (CNNs) have achieved remarkable performance on image recognition tasks.

Transformer architectures have become the dominant approach for natural language processing.

This paper provides a comprehensive survey of deep learning methods and applications."""

# 测试 POST /api/upload (TXT)
print('=== POST /api/upload (TXT) ===')
files = {'file': ('test_paper.txt', test_content.encode('utf-8'), 'text/plain')}
r = httpx.post('http://127.0.0.1:8000/api/upload', files=files)
print('Status:', r.status_code)
d = r.json()
print('success:', d['success'])
if d['success']:
    data = d['data']
    print('task_id:', data['task_id'])
    print('file_type:', data['file_type'])
    print('total_segments:', data['total_segments'])
    print('parse_duration_ms:', data['parse_duration_ms'], 'ms')
    print('Segments:')
    for seg in data['segments']:
        print(f"  [{seg['index']}] page={seg['page']} type={seg['type']} text={seg['text'][:50]}...")
    
    task_id = data['task_id']
    segments = data['segments']
    
    # 测试 GET /api/status/{task_id}
    print(f'\n=== GET /api/status/{task_id} ===')
    r2 = httpx.get(f'http://127.0.0.1:8000/api/status/{task_id}')
    d2 = r2.json()
    print('Status:', r2.status_code)
    print('task status:', d2['data']['status'])
    print('progress:', d2['data']['progress'])
    print('total_segments:', d2['data']['total_segments'])
else:
    print('Error:', d['message'])

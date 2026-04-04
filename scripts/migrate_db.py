"""
数据库迁移脚本：添加 total_segments / translated_segments 字段
"""
import sqlite3
from pathlib import Path

db_path = Path.home() / ".taixuan_translator" / "taixuan.db"
print(f"DB path: {db_path}")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# 检查现有列
cursor.execute("PRAGMA table_info(translation_tasks)")
cols = [row[1] for row in cursor.fetchall()]
print("Current columns:", cols)

# 添加缺失字段
migrations = [
    ("total_segments",      "ALTER TABLE translation_tasks ADD COLUMN total_segments INTEGER DEFAULT 0"),
    ("translated_segments", "ALTER TABLE translation_tasks ADD COLUMN translated_segments INTEGER DEFAULT 0"),
]

for col_name, sql in migrations:
    if col_name not in cols:
        cursor.execute(sql)
        print(f"Added column: {col_name}")
    else:
        print(f"Column already exists: {col_name}")

conn.commit()
conn.close()
print("Migration complete.")

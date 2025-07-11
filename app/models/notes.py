import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict
import logging

from .database import DB_PATH

# 初始化 logger
logger = logging.getLogger(__name__)

# 圖片資料夾
IMAGE_DIR = Path("/opt/crypto_alert_system/images")
IMAGE_DIR.mkdir(exist_ok=True)

IMG_TAG_RE = re.compile(r'<img\s+[^>]*src="([^"]+)"')


def extract_used_images(html: str):
    """從 HTML 中擷取使用到的圖片名稱"""
    return [Path(src).name for src in IMG_TAG_RE.findall(html or "") if "/images/" in src]


def save_note(data: Dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat(sep=' ')
    code_html = data.get("code", "")
    used_images = extract_used_images(code_html)

    if data.get("id"):
        # === 更新筆記 ===
        cursor.execute("SELECT code FROM notes WHERE id = ?", (data["id"],))
        old_row = cursor.fetchone()
        old_images = extract_used_images(old_row[0]) if old_row else []

        cursor.execute("""
            UPDATE notes
            SET title = ?, code = ?, purpose = ?, result = ?, updated_at = ?
            WHERE id = ?
        """, (
            data["title"],
            code_html,
            data.get("purpose", ""),
            data.get("result", ""),
            now,
            data["id"]
        ))
        note_id = data["id"]

        # === 刪除未使用圖片（暫時註解以避免新貼圖誤刪） ===
        # for img in set(old_images) - set(used_images):
        #     try:
        #         img_path = IMAGE_DIR / img
        #         if img_path.exists():
        #             logger.info(f"[save_note] 刪除未用圖片: {img_path}")
        #             img_path.unlink()
        #     except Exception as e:
        #         logger.error(f"[save_note] 刪除圖片失敗: {e}")
    else:
        # === 新增筆記 ===
        cursor.execute("""
            INSERT INTO notes (title, code, purpose, result, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["title"],
            code_html,
            data.get("purpose", ""),
            data.get("result", ""),
            now,
            now
        ))
        note_id = cursor.lastrowid

    conn.commit()
    conn.close()
    logger.info(f"[save_note] 筆記儲存完成 ID={note_id}")
    return note_id


def delete_note(note_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查圖片並刪除
    cursor.execute("SELECT code FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    if row:
        images = extract_used_images(row[0])
        for img in images:
            try:
                img_path = IMAGE_DIR / img
                if img_path.exists():
                    logger.info(f"[delete_note] 刪除圖片: {img_path}")
                    img_path.unlink()
            except Exception as e:
                logger.error(f"[delete_note] 刪除圖片失敗: {e}")

    # 刪除筆記資料
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    logger.info(f"[delete_note] 筆記刪除完成 ID={note_id}")

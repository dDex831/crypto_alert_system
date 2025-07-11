print("📢 run.py 被執行了！")
import os
import json
import threading
import time
import sqlite3
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime  # 新增 datetime 的匯入
from flask import Flask, send_from_directory, request, jsonify, abort, Response
from flask_cors import CORS
from flask_socketio import SocketIO
import requests

from app.models.database import init_db, save_price, DB_PATH
from app.services.price_tracker import get_price
from app.services.binance_sync import sync_trades
from app.services.news_fetcher import fetch_daily_news
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from base64 import b64decode
import uuid
from werkzeug.utils import secure_filename
from app.models import notes as notes_model

IMAGE_DIR = "/opt/crypto_alert_system/images"
os.makedirs(IMAGE_DIR, exist_ok=True)


# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Prometheus 指標 ---
PRICE_SUCCESS = Counter(
    'price_fetch_success_total',
    '價格抓取成功次數',
    ['symbol']
)
PRICE_FAILURE = Counter(
    'price_fetch_failure_total',
    '價格抓取失敗次數',
    ['symbol']
)
PRICE_DURATION = Histogram(
    'price_fetch_duration_seconds',
    '價格抓取耗時 (秒)',
    ['symbol']
)
PRICE_EMIT = Counter(
    'price_emit_total',
    '推送價格更新次數',
    ['symbol']
)

# === 1. 讀取 config.json ===
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(BASE_DIR, "config.json"), "r") as f:
    cfg = json.load(f)

SYMBOL = cfg.get("symbol", "cardano")
THRESHOLD_LOW = cfg.get("threshold_low", 0.5)
THRESHOLD_HIGH = cfg.get("threshold_high", 0.8)

# === Email 設定 & 發信函式 ===
EMAIL_SENDER   = cfg['email']['sender']
EMAIL_RECEIVER = cfg['email']['receiver']
EMAIL_PASSWORD = cfg['email']['password']

def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From']    = EMAIL_SENDER
    msg['To']      = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"[notifier] Email 已發送: {subject}")
    except Exception as e:
        logger.error(f"[notifier] 發送 Email 失敗: {e}")

# === 2. 建立 Flask + SocketIO ===
app = Flask(
    __name__,
    static_folder="frontend/build",
    static_url_path=""
)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# === 3. 初始化 DB 與同步首次交易 ===
init_db()
sync_trades()

# === 4. SPA 路由 fallback ===
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    build_dir = app.static_folder
    if path and os.path.exists(os.path.join(build_dir, path)):
        return send_from_directory(build_dir, path)
    return send_from_directory(build_dir, "index.html")

# === 5. API Endpoints ===
@app.route("/api/price")
def api_price():
    with PRICE_DURATION.labels(symbol=SYMBOL).time():
        try:
            price = get_price(SYMBOL)
            PRICE_SUCCESS.labels(symbol=SYMBOL).inc()
        except Exception as e:
            PRICE_FAILURE.labels(symbol=SYMBOL).inc()
            logger.error(f"[api_price] get_price error: {e}")
            return jsonify({"symbol": SYMBOL, "price": None}), 200
    return jsonify({"symbol": SYMBOL, "price": price})

@app.route("/api/set-threshold", methods=["POST"])
def api_set_threshold():
    global SYMBOL, THRESHOLD_LOW, THRESHOLD_HIGH, cfg

    data = request.json or {}
    SYMBOL            = data.get("symbol", SYMBOL)
    THRESHOLD_LOW     = data.get("low", THRESHOLD_LOW)
    THRESHOLD_HIGH    = data.get("high", THRESHOLD_HIGH)

    cfg.update({
        "symbol":         SYMBOL,
        "threshold_low":  THRESHOLD_LOW,
        "threshold_high": THRESHOLD_HIGH
    })
    with open(os.path.join(BASE_DIR, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    return jsonify({"ok": True})

@app.route("/api/trades")
def api_trades():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
      SELECT order_id, symbol, side, price,
             SUM(quantity) AS quantity,
             MIN(trade_time) AS trade_time
      FROM trade_history
      GROUP BY order_id
      ORDER BY datetime(trade_time) ASC
    """)
    records = cur.fetchall()
    conn.close()

    trades = []
    last_buy = {}
    for order_id, sym, side, price, qty, ttime in records:
        profit_pct = None
        if side.upper() == "BUY":
            last_buy[sym] = price
        elif side.upper() == "SELL" and last_buy.get(sym):
            bp = last_buy[sym]
            profit_pct = (price - bp) / bp * 100
        trades.append({
            "trade_time": ttime,
            "symbol": sym,
            "side": side.upper(),
            "price": price,
            "quantity": qty,
            "profit_pct": f"{profit_pct:+.2f}%" if profit_pct is not None else "-"
        })
    return jsonify(list(reversed(trades))[:50])

@app.route("/api/news")
def api_news():
    # 原 fetch_daily_news() 返回 {'blockchain': [...], 'economy': [...], 'price': ...}
    d = fetch_daily_news()

    # 合并两类新闻
    combined = d.get("blockchain", []) + d.get("economy", [])

    # 按时间戳挑最新一条
    def _ts(item):
        iso = item.get("publishedAt")
        if iso:
            try:
                return datetime.fromisoformat(iso.replace("Z", "+00:00"))
            except:
                pass
        ts = item.get("published_on")
        if ts:
            return datetime.utcfromtimestamp(ts)
        return datetime.min

    if combined:
        latest = max(combined, key=_ts)
        articles = [latest]
    else:
        articles = []

    return jsonify({
        "price": d.get("price"),
        "articles": articles
    })


# Notes CRUD Same...
@app.route("/api/notes", methods=["GET"])
def list_notes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM notes ORDER BY updated_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ... update, delete omitted for brevity

@app.route("/api/config")
def api_config():
    return jsonify({
        "symbol": cfg.get("symbol", SYMBOL),
        "threshold_low": cfg.get("threshold_low", THRESHOLD_LOW),
        "threshold_high": cfg.get("threshold_high", THRESHOLD_HIGH)
    })

@app.route("/metrics")
def metrics():
    data = generate_latest()
    return Response(data, mimetype=CONTENT_TYPE_LATEST)

@socketio.on("connect")
def on_connect():
    try:
        price = get_price(SYMBOL)
        socketio.emit(
            "price_update",
            {"symbol": SYMBOL, "price": price},
            to=request.sid
        )
    except Exception as e:
        logger.error(f"[on_connect] 推送初始價格失敗: {e}")


def price_broadcast_thread():
    alert_high_sent = False
    alert_low_sent = False
    while True:
        try:
            with PRICE_DURATION.labels(symbol=SYMBOL).time():
                price = get_price(SYMBOL)
            PRICE_SUCCESS.labels(symbol=SYMBOL).inc()
        except Exception as e:
            PRICE_FAILURE.labels(symbol=SYMBOL).inc()
            logger.error(f"[broadcast] get_price error: {e}")
            time.sleep(30)
            continue

        if price is not None:
            save_price(SYMBOL, price)
            PRICE_EMIT.labels(symbol=SYMBOL).inc()
            socketio.emit("price_update", { "symbol": SYMBOL, "price": price })

            if price > THRESHOLD_HIGH and not alert_high_sent:
                send_email(
                    f"{SYMBOL.upper()} 價格高於 {THRESHOLD_HIGH}",
                    f"目前價格 ${price:.4f}，請注意可能逢高。"
                )
                alert_high_sent = True
                alert_low_sent = False
            elif price < THRESHOLD_LOW and not alert_low_sent:
                send_email(
                    f"{SYMBOL.upper()} 價格低於 {THRESHOLD_LOW}",
                    f"目前價格 ${price:.4f}，可考慮加倉。"
                )
                alert_low_sent = True
                alert_high_sent = False

        time.sleep(60)

def scheduled_news_fetch():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            try:
                logger.info("⏰ 開始每日新聞抓取")
                fetch_daily_news()
            except Exception as e:
                logger.error(f"[news_fetch] 抓取新聞失敗: {e}")
            time.sleep(60)  # 避免重複執行
        time.sleep(30)

def scheduled_trade_sync():
    while True:
        try:
            logger.info("🔄 同步 Binance 交易紀錄")
            sync_trades()
        except Exception as e:
            logger.error(f"[sync_trades] 同步交易紀錄失敗: {e}")
        time.sleep(3600)  # 每小時抓一次

# === 6. 圖片上傳與存取 ===
@app.route("/api/upload_image", methods=["POST"])
def upload_image():
    data = request.get_json()
    base64_data = data.get("image")
    if not base64_data or not base64_data.startswith("data:image/"):
        return jsonify({"error": "Invalid image data"}), 400

    try:
        header, encoded = base64_data.split(",", 1)
        file_ext = header.split("/")[1].split(";")[0]
        filename = f"img_{uuid.uuid4().hex}.{file_ext}"
        filepath = os.path.join(IMAGE_DIR, secure_filename(filename))
        with open(filepath, "wb") as f:
            f.write(b64decode(encoded))
        return jsonify({"url": f"/images/{filename}"})
    except Exception as e:
        logger.error(f"[upload_image] 圖片儲存失敗: {e}")
        return jsonify({"error": "Failed to save image"}), 500

@app.route("/api/notes", methods=["POST"])
def create_note():
    data = request.get_json()
    try:
        note_id = notes_model.save_note(data)
        return jsonify({"ok": True, "id": note_id})
    except Exception as e:
        logger.error(f"[create_note] 儲存筆記失敗: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.get_json()
    data["id"] = note_id
    try:
        notes_model.save_note(data)
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"[update_note] 更新筆記失敗: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    try:
        notes_model.delete_note(note_id)
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"[delete_note] 刪除筆記失敗: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# === 7. 啟動 Server ===
if __name__ == "__main__":
    print("🔄 伺服器啟動中...")
    init_db()
    sync_trades()
    
    # 即時價格推送
    thread = threading.Thread(target=price_broadcast_thread)
    thread.daemon = True
    thread.start()

    # 排程任務
    news_thread = threading.Thread(target=scheduled_news_fetch)
    news_thread.daemon = True
    news_thread.start()

    trade_thread = threading.Thread(target=scheduled_trade_sync)
    trade_thread.daemon = True
    trade_thread.start()

    # 啟動 Flask Server
    socketio.run(app, host="0.0.0.0", port=5000)


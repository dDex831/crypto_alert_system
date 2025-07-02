import os
import json
import threading
import time
import sqlite3
import smtplib
from email.mime.text import MIMEText

from flask import Flask, send_from_directory, request, jsonify, abort, Response
from flask_cors import CORS
from flask_socketio import SocketIO

from app.models.database import init_db, save_price, DB_PATH
from app.services.price_tracker import get_price
from app.services.binance_sync import sync_trades
from app.services.news_fetcher import fetch_daily_news
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


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
            server.set_debuglevel(0)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        app.logger.info(f"[notifier] Email 已發送: {subject}")
    except Exception as e:
        app.logger.error(f"[notifier] 發送 Email 失敗: {e}")

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
            app.logger.error(f"[api_price] get_price error: {e}")
            return jsonify({"symbol": SYMBOL, "price": None}), 200
    return jsonify({"symbol": SYMBOL, "price": price})

@app.route("/api/set-threshold", methods=["POST"])
def api_set_threshold():
    data = request.json or {}
    cfg.update({
        "symbol": data.get("symbol", SYMBOL),
        "threshold_low": data.get("low", THRESHOLD_LOW),
        "threshold_high": data.get("high", THRESHOLD_HIGH)
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
    return jsonify(fetch_daily_news())

# Notes CRUD...
@app.route("/api/notes", methods=["GET"])
def list_notes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM notes ORDER BY updated_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/notes", methods=["POST"])
def create_note():
    data = request.json or {}
    if not data.get("title"):
        abort(400, "title required")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (title,code,explanation,purpose,result) VALUES (?,?,?,?,?)",
        (data["title"], data.get("code",""), data.get("explanation",""),
         data.get("purpose",""), data.get("result",""))
    )
    nid = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"id": nid}), 201

@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.json or {}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE notes SET title=?,code=?,explanation=?,purpose=?,result=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (data.get("title"), data.get("code",""), data.get("explanation",""),
         data.get("purpose",""), data.get("result",""), note_id)
    )
    if cur.rowcount == 0:
        conn.close()
        abort(404)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE id=?", (note_id,))
    if cur.rowcount == 0:
        conn.close()
        abort(404)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

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
        app.logger.error(f"[on_connect] 推送初始價格失敗: {e}")


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
            app.logger.error(f"[broadcast] get_price error: {e}")
            time.sleep(30)
            continue

        if price is not None:
            save_price(SYMBOL, price)
            PRICE_EMIT.labels(symbol=SYMBOL).inc()
            socketio.emit("price_update", { "symbol": SYMBOL, "price": price })

            # 價格高於閾值且尚未發過高價通知
            if price > THRESHOLD_HIGH and not alert_high_sent:
                subject = f"{SYMBOL.upper()} 價格高於 {THRESHOLD_HIGH}"
                body = f"目前價格 ${price:.4f}，請注意可能逢高。"
                send_email(subject, body)
                alert_high_sent = True
                alert_low_sent = False

            # 價格低於閾值且尚未發過低價通知
            elif price < THRESHOLD_LOW and not alert_low_sent:
                subject = f"{SYMBOL.upper()} 價格低於 {THRESHOLD_LOW}"
                body = f"目前價格 ${price:.4f}，可考慮加倉。"
                send_email(subject, body)
                alert_low_sent = True
                alert_high_sent = False

        time.sleep(60)


# === 7. 啟動 Server ===
if __name__ == "__main__":
    sync_trades()
    thread = threading.Thread(target=price_broadcast_thread)
    thread.daemon = True
    thread.start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

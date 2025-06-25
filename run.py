# run.py

import os
import json
import threading
import time
import sqlite3

from flask import Flask, send_from_directory, request, jsonify, abort
from flask_cors import CORS
from flask_socketio import SocketIO

from app.models.database import init_db, save_price, DB_PATH
from app.services.price_tracker import get_price
from app.services.binance_sync import sync_trades
from app.services.news_fetcher import fetch_daily_news

# === 1. 讀取 config.json ===
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(BASE_DIR, "config.json"), "r") as f:
    cfg = json.load(f)

SYMBOL = cfg.get("symbol", "cardano")
THRESHOLD_LOW = cfg.get("threshold_low", 0.5)
THRESHOLD_HIGH = cfg.get("threshold_high", 0.8)

# === 2. 建立 Flask + SocketIO ===
app = Flask(
    __name__,
    static_folder="frontend/build",  # build 輸出
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
    """若請求的檔案存在就回傳，否則回傳 index.html 給 React Router"""
    build_dir = app.static_folder
    if path and os.path.exists(os.path.join(build_dir, path)):
        return send_from_directory(build_dir, path)
    return send_from_directory(build_dir, "index.html")

# === 5. API Endpoints ===
@app.route("/api/price")
def api_price():
    try:
        price = get_price(SYMBOL)
    except Exception as e:
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
    """
    回傳目前的 symbol 與 threshold 設定
    """
    # 讀取最新 cfg（這裡假設 cfg 已在全域保持最新）
    return jsonify({
        "symbol": cfg.get("symbol", SYMBOL),
        "threshold_low": cfg.get("threshold_low", THRESHOLD_LOW),
        "threshold_high": cfg.get("threshold_high", THRESHOLD_HIGH)
    })

@socketio.on("connect")
def on_connect():
    """客戶端連線時，立刻推送一次當前價格"""
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
    """
    每 30 秒抓一次，寫庫、並固定推送最新價格。
    """
    while True:
        try:
            price = get_price(SYMBOL)
        except Exception as e:
            app.logger.error(f"[broadcast] get_price error: {e}")
            time.sleep(30)
            continue

        if price is not None:
            save_price(SYMBOL, price)
            app.logger.info(f"emit price_update: {SYMBOL} {price}")
            socketio.emit("price_update", {
                "symbol": SYMBOL,
                "price": price
            })

        time.sleep(60)

# === 7. 啟動 Server ===
if __name__ == "__main__":
    sync_trades()
    thread = threading.Thread(target=price_broadcast_thread)
    thread.daemon = True
    thread.start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

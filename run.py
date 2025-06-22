from flask import Flask, send_from_directory, request, jsonify, abort
import sqlite3
import json
from app.models.database import init_db, DB_PATH
from app.services.price_tracker import get_price
from app.services.binance_sync import sync_trades
from app.services.news_fetcher import fetch_daily_news

app = Flask(
    __name__,
    static_folder="frontend",
    static_url_path=""
)

# 啟動時建立表格並拉取一次交易
init_db()
sync_trades()

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/price")
def api_price():
    symbol = request.args.get("symbol", "cardano")
    price = get_price(symbol)
    return jsonify({"symbol": symbol, "price": price})

@app.route("/api/set-threshold", methods=["POST"])
def api_set_threshold():
    data = request.json
    with open("config.json", "r+") as f:
        cfg = json.load(f)
        cfg.update({
            "symbol": data["symbol"],
            "threshold_low": data["low"],
            "threshold_high": data["high"]
        })
        f.seek(0); f.truncate(); json.dump(cfg, f, indent=2)
    return jsonify({"ok": True})

@app.route("/api/trades")
def api_trades():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
      SELECT order_id, symbol, side, price, SUM(quantity) AS quantity, MIN(trade_time) AS trade_time
      FROM trade_history
      GROUP BY order_id
      ORDER BY datetime(trade_time) ASC
    """
    )
    records = cur.fetchall()
    conn.close()

    trades = []
    last_buy = {}
    for order_id, symbol, side, price, qty, ttime in records:
        profit_pct = None
        side_u = side.upper()
        if side_u == "BUY":
            last_buy[symbol] = price
        elif side_u == "SELL":
            bp = last_buy.get(symbol)
            if bp and bp > 0:
                profit_pct = (price - bp) / bp * 100
        trades.append({
            "trade_time": ttime,
            "symbol": symbol,
            "side": side_u,
            "price": price,
            "quantity": qty,
            "profit_pct": f"{profit_pct:+.2f}%" if profit_pct is not None else "-"
        })
    trades = list(reversed(trades))[:50]
    return jsonify(trades)

@app.route("/api/news")
def api_news():
    daily = fetch_daily_news()
    return jsonify(daily)

# CRUD for notes
@app.route("/api/notes", methods=["GET"])
def list_notes():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM notes ORDER BY updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    notes = [dict(row) for row in rows]
    return jsonify(notes)

@app.route("/api/notes", methods=["POST"])
def create_note():
    data = request.json or {}
    # 只強制檢查 title
    if not data.get("title"):
        return abort(400, description="title required")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (title,code,explanation,purpose,result) VALUES (?,?,?,?,?)",
        (
            data["title"],
            data.get("code", ""),        # code 可為空
            data.get("explanation", ""),
            data.get("purpose", ""),
            data.get("result", "")
        )
    )
    nid = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"id": nid}), 201


@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE notes SET title=?, code=?, explanation=?, purpose=?, result=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (data.get("title"), data.get("code"), data.get("explanation",""), data.get("purpose",""), data.get("result",""), note_id)
    )
    if cur.rowcount == 0:
        conn.close()
        return abort(404)
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
        return abort(404)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)

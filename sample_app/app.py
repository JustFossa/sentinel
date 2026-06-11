"""Tiny checkout service used to stage the demo incident.

Run the healthy version, fire some traffic (all 200s), then flip
CHECKOUT_VERSION=buggy and restart to reproduce commit a3f9c21 — the checkout
endpoint starts throwing KeyError('tax_rate') → HTTP 500, exactly the incident
Sentinel diagnoses.

    pip install flask
    python sample_app/app.py                  # healthy
    CHECKOUT_VERSION=buggy python sample_app/app.py   # broken on cue

    curl -s -X POST localhost:5000/api/checkout -H 'content-type: application/json' \
         -d '{"items":[{"sku":"BOOK-1","price":12.0,"tax_rate":0.08},
                        {"sku":"GIFTCARD-9","price":50.0}]}'
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

app = Flask(__name__)
DEFAULT_TAX = 0.0
BUGGY = os.getenv("CHECKOUT_VERSION", "healthy") == "buggy"


def calculate_total(items: list[dict]) -> float:
    total = 0.0
    for item in items:
        price = item["price"]
        if BUGGY:
            # commit a3f9c21 "refactor: simplify tax calculation" — removed the
            # fallback. Gift cards (no tax category) now raise KeyError('tax_rate').
            tax = item["tax_rate"]
        else:
            tax = item.get("tax_rate", DEFAULT_TAX)
        total += price * (1 + tax)
    return round(total, 2)


@app.post("/api/checkout")
def checkout():
    body = request.get_json(force=True, silent=True) or {}
    items = body.get("items", [])
    total = calculate_total(items)            # raises KeyError in buggy build
    return jsonify({"status": "ok", "total": total})


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "version": "buggy" if BUGGY else "healthy"})


if __name__ == "__main__":
    print(f"checkout-service starting (version={'buggy' if BUGGY else 'healthy'})")
    app.run(host="0.0.0.0", port=5000)

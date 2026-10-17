#!/usr/bin/env python3
"""Sanity-check launches.json and rumors.json before building. Exit 1 on any problem."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CATS = {"apple", "android", "samsung", "ai", "gaming", "chips", "evs"}
STATUS = {"Confirmed", "Expected", "Estimated", "Released"}
PREC = {"day", "window"}
RATINGS = {"Confirmed", "Likely", "Rumor", "Shaky", "Debunked"}
RSTATUS = {"Active", "Resolved"}
errs = []

def need(obj, keys, label):
    for k in keys:
        if k not in obj or obj[k] in (None, ""):
            if k in ("price",):
                continue
            errs.append(f"{label}: missing {k}")

def srcs(obj, label):
    if not obj.get("sources"):
        errs.append(f"{label}: needs at least one source")
    for s in obj.get("sources", []):
        if not str(s.get("url", "")).startswith("https://"):
            errs.append(f"{label}: bad source url {s.get('url')}")

ids = set()
for i in json.loads((ROOT / "launches.json").read_text())["items"]:
    L = "launch " + i.get("id", "?")
    need(i, ["id", "name", "brand", "categories", "type", "date", "date_label", "precision", "status", "summary", "details"], L)
    if i["id"] in ids: errs.append(L + ": duplicate id")
    ids.add(i["id"])
    if not re.fullmatch(r"[a-z0-9-]+", i["id"]): errs.append(L + ": id must be lowercase-hyphen")
    if i["status"] not in STATUS: errs.append(L + ": bad status")
    if i["precision"] not in PREC: errs.append(L + ": bad precision")
    if not set(i["categories"]) <= CATS: errs.append(L + ": bad category")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", i["date"]): errs.append(L + ": date must be YYYY-MM-DD")
    srcs(i, L)

ids = set()
for r in json.loads((ROOT / "rumors.json").read_text())["items"]:
    L = "rumor " + r.get("id", "?")
    need(r, ["id", "title", "rating", "categories", "status", "updated", "claim", "why"], L)
    if r["id"] in ids: errs.append(L + ": duplicate id")
    ids.add(r["id"])
    if r["rating"] not in RATINGS: errs.append(L + ": bad rating")
    if r["status"] not in RSTATUS: errs.append(L + ": bad status")
    if not set(r["categories"]) <= CATS: errs.append(L + ": bad category")
    srcs(r, L)

if errs:
    print("\n".join(errs)); sys.exit(1)
print("data OK")

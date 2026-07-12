#!/usr/bin/env python3
"""
Generates data.json for the Gamma Ray Dashboard GitHub Pages site.
Reads from ~/Projects/gamma-ray/data/ledger.db

Usage:
    python3 generate_data.py          # writes data.json next to this script
    python3 generate_data.py --dry-run  # prints JSON, doesn't write
"""
import json, sys, sqlite3
from pathlib import Path
from datetime import datetime

GAMMA_DIR = Path.home() / "Projects/gamma-ray"
OUT_FILE  = Path(__file__).parent / "data.json"

def load_ledger():
    db_path = GAMMA_DIR / "data/ledger.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT outcome, COUNT(*) as n, ROUND(SUM(pnl),2) as pnl, ROUND(SUM(size_usd),2) as risked FROM bets WHERE outcome IS NOT NULL GROUP BY outcome")
    outcomes = {r["outcome"]: dict(r) for r in c.fetchall()}
    wins   = outcomes.get("win",   {"n": 0, "pnl": 0, "risked": 0})
    losses = outcomes.get("loss",  {"n": 0, "pnl": 0, "risked": 0})
    voided = outcomes.get("voided",{"n": 0, "pnl": 0, "risked": 0})
    total_w = wins["n"]; total_l = losses["n"]
    total_pnl    = round((wins["pnl"] or 0) + (losses["pnl"] or 0), 2)
    total_risked = round((wins["risked"] or 0) + (losses["risked"] or 0), 2)
    win_rate = round(total_w / (total_w + total_l) * 100, 1) if (total_w + total_l) else 0
    roi      = round(total_pnl / total_risked * 100, 1) if total_risked else 0

    c.execute("""SELECT side, outcome, COUNT(*) as n, ROUND(SUM(pnl),2) as pnl,
                 ROUND(SUM(size_usd),2) as size_usd
                 FROM bets WHERE outcome IN ('win','loss') GROUP BY side, outcome""")
    sr = c.fetchall()
    def sg(side, out, k): return next((r[k] for r in sr if r["side"]==side and r["outcome"]==out), 0) or 0
    yes_w=sg("yes","win","n"); yes_l=sg("yes","loss","n")
    no_w =sg("no","win","n");  no_l =sg("no","loss","n")
    yes_pnl=round(sg("yes","win","pnl")+sg("yes","loss","pnl"),2)
    no_pnl =round(sg("no","win","pnl") +sg("no","loss","pnl"),2)
    yes_risked=sg("yes","win","size_usd")+sg("yes","loss","size_usd") or 1
    no_risked =sg("no","win","size_usd") +sg("no","loss","size_usd")  or 1

    c.execute("""SELECT CASE WHEN our_prob<0.5 THEN '<50' WHEN our_prob<0.6 THEN '50-60'
                 WHEN our_prob<0.7 THEN '60-70' WHEN our_prob<0.8 THEN '70-80' ELSE '80+'
                 END as bucket, COUNT(*) as total,
                 SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
                 ROUND(SUM(pnl),2) as pnl
                 FROM bets WHERE outcome IN ('win','loss') GROUP BY bucket ORDER BY bucket""")
    calib = [dict(r) for r in c.fetchall()]
    for b in calib:
        b["win_rate"] = round(b["wins"] / b["total"] * 100, 1) if b["total"] else 0

    c.execute("""SELECT market_id, question, side, size_usd, price_cents,
                 our_prob, edge, outcome, pnl, placed_at
                 FROM bets WHERE outcome IN ('win','loss')
                 ORDER BY placed_at DESC LIMIT 15""")
    recent = [dict(r) for r in c.fetchall()]
    for b in recent: b["placed_at"] = (b["placed_at"] or "")[:10]

    c.execute("SELECT market_id, question, side, size_usd, price_cents, placed_at FROM bets WHERE outcome IS NULL OR outcome = ''")
    open_pos = [dict(r) for r in c.fetchall()]
    for p in open_pos: p["placed_at"] = (p["placed_at"] or "")[:10]

    c.execute("SELECT outcome FROM bets WHERE outcome IN ('win','loss') ORDER BY placed_at DESC LIMIT 20")
    streak_rows = [r["outcome"] for r in c.fetchall()]
    streak=0; streak_type=streak_rows[0] if streak_rows else ""
    for o in streak_rows:
        if o==streak_type: streak+=1
        else: break
    conn.close()

    return {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M PT"),
        "total_w": total_w, "total_l": total_l, "win_rate": win_rate,
        "total_pnl": total_pnl, "total_risked": total_risked,
        "roi": roi, "voided": voided["n"],
        "yes": {"w":yes_w,"l":yes_l,"pnl":yes_pnl,
                "wr":round(yes_w/(yes_w+yes_l)*100,1) if (yes_w+yes_l) else 0,
                "roi":round(yes_pnl/yes_risked*100,1)},
        "no":  {"w":no_w, "l":no_l, "pnl":no_pnl,
                "wr":round(no_w/(no_w+no_l)*100,1)  if (no_w+no_l)  else 0,
                "roi":round(no_pnl/no_risked*100,1)},
        "calib": calib, "recent": recent, "open": open_pos,
        "streak": streak, "streak_type": streak_type,
        "balance": 184.11,
    }

if __name__ == "__main__":
    data = load_ledger()
    if "--dry-run" in sys.argv:
        print(json.dumps(data, indent=2))
    else:
        with open(OUT_FILE, "w") as f:
            json.dump(data, f)
        print(f"[gamma-data] {data['updated']} — {data['total_w']}W/{data['total_l']}L P&L ${data['total_pnl']}")

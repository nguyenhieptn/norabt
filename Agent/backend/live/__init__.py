"""Live incremental polling for the 30 selected copy-trading bots.

Everything under this package reads/writes the same on-disk dataset the
crawl-once pipeline (`Agent/none/scripts/crawl_bots.py`) and the QC steps
(`Agent/backend/pipeline.py`, `Agent/backend/report/qc/...`) already use. The goal is
narrow on purpose: keep that dataset current between full crawls without ever
re-crawling a bot's whole history, and without ever risking the existing
files -- a half-written or wrongly-emptied `trade_list.json` is worse than a
stale one, since step 2/3 cannot tell "stale" from "corrupted".
"""

from __future__ import annotations

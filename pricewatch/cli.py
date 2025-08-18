from __future__ import annotations

import argparse
import json
import os
from typing import Iterable, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import orjson

from .providers import get_provider
from .aggregator import median_market_price, select_target_merchants, annotate_discounts


def read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def write_jsonl(path: str, records: Iterable[dict]) -> None:
    with open(path, "wb") as f:
        for rec in records:
            f.write(orjson.dumps(rec))
            f.write(b"\n")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("pricewatch")
    p.add_argument("--provider", choices=["serper", "serpapi"], default="serper")
    p.add_argument("--input", required=True, help="Path to queries file (one per line)")
    p.add_argument("--output", required=True, help="Output JSONL path")
    p.add_argument("--hl", default="ar")
    p.add_argument("--gl", default="eg")
    p.add_argument("--targets", default="amazon.eg,jumia.com.eg,noon.com")
    p.add_argument("--shopping-only", action="store_true")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--concurrency", type=int, default=8)
    return p


def main() -> None:
    load_dotenv()
    args = build_arg_parser().parse_args()
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]

    provider = get_provider(args.provider, hl=args.hl, gl=args.gl, timeout_seconds=args.timeout)
    queries = read_lines(args.input)

    out_records: List[dict] = []

    def process_query(q: str) -> dict:
        raw = provider.search(q, shopping_only=args.shopping_only)
        items = provider.parse_results(raw)
        market_med = median_market_price(items)
        top_merchants = select_target_merchants(items, targets)
        annotated = annotate_discounts(top_merchants, market_med)
        return {
            "query": q,
            "hl": args.hl,
            "gl": args.gl,
            "results_count": len(items),
            "market": {"median": market_med, "currency": items[0].get("currency") if items else None},
            "top_merchants": top_merchants,
            "targets": annotated,
        }

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        future_to_query = {executor.submit(process_query, q): q for q in queries}
        for future in as_completed(future_to_query):
            try:
                out_records.append(future.result())
            except Exception as exc:
                out_records.append({
                    "query": future_to_query[future],
                    "error": str(exc),
                    "hl": args.hl,
                    "gl": args.gl,
                })

    write_jsonl(args.output, out_records)


if __name__ == "__main__":
    main()

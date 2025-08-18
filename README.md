## PriceWatch (Google SERP-based market price aggregator)

Arabic-first CLI to fetch market prices fast from Google SERP providers (Serper.dev or SerpAPI), compute market median, and compare target merchants (e.g., Amazon.eg, Jumia, Noon) — outputs JSON Lines for easy post-processing.

### Quick start
1) Install dependencies:
```bash
python -m pip install -r /workspace/requirements.txt
```

2) Set API keys (use any that you have):
```bash
# Serper.dev (recommended cheaper)
export SERPER_API_KEY="YOUR_SERPER_KEY"

# SerpAPI (optional fallback)
export SERPAPI_API_KEY="YOUR_SERPAPI_KEY"
```

3) Create a queries file (one product per line), e.g. `/workspace/queries.txt`:
```text
سوار سيليكون 22 ملم لساعة سامسونج جالاكسي 3 45
هاتف سامسونج A15 128GB
```

4) Run:
```bash
python -m pricewatch.cli \
  --provider serper \
  --input /workspace/queries.txt \
  --output /workspace/out.jsonl \
  --hl ar --gl eg \
  --targets amazon.eg,jumia.com.eg,noon.com \
  --concurrency 10
```

Options:
- `--provider`: `serper` or `serpapi`
- `--hl` language (default `ar`), `--gl` country (default `eg`)
- `--targets` comma-separated domains to highlight and compute discount vs market median
- `--shopping-only` to skip organic fallback

### Output (JSONL per product)
Each line contains the normalized results, market median, and target merchant comparisons. Example shape:
```json
{
  "query": "سوار سيليكون 22 ملم...",
  "gl": "eg",
  "hl": "ar",
  "results_count": 12,
  "market": {"median": 135.0, "currency": "EGP"},
  "top_merchants": [
    {"domain": "amazon.eg", "price": 90.0, "link": "https://..."},
    {"domain": "jumia.com.eg", "price": 150.0, "link": "https://..."}
  ],
  "targets": [
    {"domain": "amazon.eg", "price": 90.0, "discount_pct_vs_median": 33.3}
  ]
}
```

### Notes
- No site crawling is done here; we rely on SERP data for speed. If results are too sparse, enable organic fallback to parse price from snippets.
- To reduce cost and speed up, reuse queries (deduplicate) and run with reasonable concurrency.

# Buy or Wait? — Evaluation Usage Report

**Run date:** 2026-09-13 01:05:19 UTC

**Total requests processed:** 250

**Total elapsed time:** 2.7s

**Average time per request:** 10.8ms

## Model / AI Usage

This solution uses a **fully deterministic, rule-based financial engine** with no external AI/LLM calls. All decisions are computed locally from the provided CSV datasets using the following components:

| Component | Description |
|-----------|-------------|
| `data_loader.py` | Loads all CSVs, applies exchange-rate conversions, fills image-sourced amounts |
| `message_parser.py` | Parses salary/rent signals from messages.csv |
| `image_data.py` | Pre-extracted amounts from dataset/media/images/ |
| `simulator.py` | 90-day cashflow simulation with salary/expense recurrence |
| `decision_engine.py` | Evaluates full/partial/installment/wait candidates and ranks them |

## Token / Cost Summary

| Metric | Value |
|--------|-------|
| Model providers | None (no LLM used) |
| Model calls | 0 |
| Input tokens | 0 |
| Output tokens | 0 |
| Total tokens | 0 |
| Avg tokens per request | 0 |
| Estimated total cost | $0.00 |
| Estimated cost per request | $0.00 |

## Notes

- Exchange rates from `exchange_rates.csv` are applied at settlement date.
- Image amounts pre-extracted via OCR and stored in `image_data.py`.
- Messages parsed with regex for salary changes, rent adjustments, and employment end.
- Forecast window: 90 days from request date.
- All amounts in the user's home currency.

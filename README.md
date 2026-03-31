# Federal Register Market Scanner — Version 6

This is a Streamlit web app that scans the Federal Register for potentially market-relevant rules, proposed rules, notices, and optionally public-inspection documents.

## What changed in Version 6

- stronger industry-to-ticker mapping
- neutral **Regulatory Significance** separated from directional **Market Stance**
- tighter score spread so fewer items cluster at the top
- deterministic "Why this matters" mapping by primary industry
- disclaimer and validation badges
- Unified Agenda forward-look tab

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

- repo name: `fedreg-stock-scanner`
- branch: `main`
- main file path: `app.py`

## Notes

This tool is for research and monitoring only. It is not investment, legal, or tax advice.

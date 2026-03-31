SECTOR_TICKERS = {
    "Banks & Financials": ["JPM", "BAC", "GS"],
    "Energy & Utilities": ["XOM", "CVX", "NEE"],
    "Defense & Aerospace": ["BA", "RTX", "LMT"],
    "Healthcare & Pharma": ["LLY", "JNJ", "PFE"],
    "Autos & EV": ["TSLA", "GM", "F"],
    "Semiconductors & AI": ["NVDA", "AMD", "AVGO"],
    "Consumer & Retail": ["WMT", "COST", "TGT"],
    "Big Tech & Internet": ["MSFT", "AMZN", "GOOGL"],
    "Industrials & Transport": ["UNP", "CAT", "CSX"],
}


def get_tickers(industry: str) -> list[str]:
    return SECTOR_TICKERS.get(industry, [])

WHY_MAP = {
    "Banks & Financials": "Could affect capital requirements, lending activity, liquidity, or funding costs.",
    "Energy & Utilities": "Could impact energy supply, permitting, infrastructure investment, or regulatory approvals.",
    "Defense & Aerospace": "Could affect aircraft operations, safety compliance, supplier costs, or maintenance cycles.",
    "Healthcare & Pharma": "Could alter approvals, compliance requirements, reimbursement, or drug/device demand.",
    "Autos & EV": "Could influence manufacturing costs, safety compliance, recalls, or EV adoption.",
    "Semiconductors & AI": "Could impact chip supply chains, trade restrictions, pricing, or AI infrastructure demand.",
    "Consumer & Retail": "Could affect product standards, imports, recalls, or retail compliance costs.",
    "Big Tech & Internet": "Could affect data handling, cloud demand, platform compliance, or digital-service costs.",
    "Industrials & Transport": "Could affect freight flows, logistics costs, industrial demand, or transportation compliance.",
}


def get_why(industry: str) -> str:
    return WHY_MAP.get(industry, "Could impact industry conditions, compliance costs, or demand.")

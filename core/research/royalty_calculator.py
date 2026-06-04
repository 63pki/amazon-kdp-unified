"""
KDP Royalty Calculator & Revenue Projector
==========================================
Calculate royalties, break-even points, and monthly revenue
projections for Amazon KDP eBook and Print-on-Demand titles.

Author : Alexie Le
GitHub : https://github.com/alexiale123456789
"""

import pandas as pd


# ── Core Calculator ──────────────────────────────────────────────

def kdp_royalty_calculator(price: float,
                            pages: int,
                            is_print: bool = False,
                            monthly_sales: int = 100) -> dict:
    """
    Calculate KDP royalties and monthly revenue projection.

    Args:
        price         : Listed book price in USD
        pages         : Number of pages (required for print cost)
        is_print      : True = Print-on-Demand, False = eBook
        monthly_sales : Estimated units sold per month

    Returns:
        dict with royalty breakdown and revenue projection
    """
    if is_print:
        printing_cost    = round(0.85 + (0.012 * pages), 2)
        royalty_per_sale = round(max(0, (price * 0.60) - printing_cost), 2)
        royalty_rate     = "60%"
        format_type      = "Print-on-Demand"
    else:
        rate             = 0.70 if 2.99 <= price <= 9.99 else 0.35
        royalty_per_sale = round(price * rate, 2)
        royalty_rate     = f"{int(rate * 100)}%"
        printing_cost    = 0.0
        format_type      = "eBook"

    monthly_revenue = round(royalty_per_sale * monthly_sales, 2)
    annual_revenue  = round(monthly_revenue * 12, 2)
    sales_to_100    = round(100 / royalty_per_sale, 1) if royalty_per_sale > 0 else "N/A"

    return {
        "Format"             : format_type,
        "Price"              : f"${price:.2f}",
        "Royalty Rate"       : royalty_rate,
        "Printing Cost"      : f"${printing_cost:.2f}" if is_print else "—",
        "Royalty / Sale"     : f"${royalty_per_sale:.2f}",
        "Est. Monthly Sales" : monthly_sales,
        "Monthly Revenue"    : f"${monthly_revenue:,.2f}",
        "Annual Revenue"     : f"${annual_revenue:,.2f}",
        "Sales to $100"      : sales_to_100,
    }


# ── Tier Comparison ──────────────────────────────────────────────

def generate_tier_comparison() -> pd.DataFrame:
    """
    Generate the 4-tier revenue projection model.

    Returns:
        DataFrame showing all book tiers side by side
    """
    tiers = [
        {
            "Tier"        : "📗 Market Test",
            "Pages"       : 20,
            "Price"       : 1.99,
            "Monthly Sales": 30,
            "Strategy"    : "Validate demand fast"
        },
        {
            "Tier"        : "📘 Standard Non-Fiction",
            "Pages"       : 100,
            "Price"       : 5.99,
            "Monthly Sales": 70,
            "Strategy"    : "Solve one specific problem"
        },
        {
            "Tier"        : "📙 Legacy Asset",
            "Pages"       : 210,
            "Price"       : 9.99,
            "Monthly Sales": 120,
            "Strategy"    : "Authority + long-term BSR"
        },
        {
            "Tier"        : "📚 Catalog Play",
            "Pages"       : 120,
            "Price"       : 6.99,
            "Monthly Sales": 200,
            "Strategy"    : "Volume × compounding income"
        },
    ]

    rows = []
    for t in tiers:
        calc = kdp_royalty_calculator(
            price         = t["Price"],
            pages         = t["Pages"],
            monthly_sales = t["Monthly Sales"]
        )
        rows.append({
            "Tier"              : t["Tier"],
            "Pages"             : t["Pages"],
            "Price"             : calc["Price"],
            "Royalty/Sale"      : calc["Royalty / Sale"],
            "Est. Monthly Sales": t["Monthly Sales"],
            "Monthly Revenue"   : calc["Monthly Revenue"],
            "Annual Revenue"    : calc["Annual Revenue"],
            "Strategy"          : t["Strategy"],
        })

    return pd.DataFrame(rows)


# ── Break-Even Analyzer ──────────────────────────────────────────

def break_even_analysis(price: float,
                         pages: int,
                         production_cost: float = 0,
                         monthly_ad_spend: float = 0,
                         is_print: bool = False) -> dict:
    """
    Calculate break-even point given production and marketing costs.

    Args:
        price            : Book price in USD
        pages            : Number of pages
        production_cost  : One-time cost (editing, cover design, etc.)
        monthly_ad_spend : Monthly Amazon Ads budget
        is_print         : True for Print-on-Demand

    Returns:
        dict with break-even units and timeline
    """
    calc             = kdp_royalty_calculator(price, pages, is_print, 1)
    royalty_str      = calc["Royalty / Sale"].replace("$", "")
    royalty_per_sale = float(royalty_str)

    if royalty_per_sale <= 0:
        return {"error": "Price too low — royalty is $0 after printing costs."}

    units_to_cover_production = round(production_cost / royalty_per_sale, 1)
    monthly_units_for_ads     = round(monthly_ad_spend / royalty_per_sale, 1) if monthly_ad_spend > 0 else 0

    return {
        "Royalty / Sale"            : f"${royalty_per_sale:.2f}",
        "Production Cost"           : f"${production_cost:.2f}",
        "Units to Break Even"       : units_to_cover_production,
        "Monthly Ad Spend"          : f"${monthly_ad_spend:.2f}",
        "Monthly Units for Ads"     : monthly_units_for_ads,
        "Net Positive From Unit"    : int(units_to_cover_production) + 1,
    }


# ── Main Demo ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  KDP ROYALTY CALCULATOR — by Alexie Le")
    print("="*60)

    # Single book example
    print("\n📘 Single Book Analysis — $5.99 eBook, 120 pages, 80 sales/mo")
    result = kdp_royalty_calculator(price=5.99, pages=120, monthly_sales=80)
    for k, v in result.items():
        print(f"  {k:<22}: {v}")

    # Tier comparison
    print("\n\n📊 Revenue Projection — All 4 Tiers")
    print("-"*60)
    df = generate_tier_comparison()
    print(df.to_string(index=False))
    df.to_csv("revenue_projections.csv", index=False)
    print("\n  Saved → revenue_projections.csv")

    # Break-even example
    print("\n\n🔍 Break-Even Analysis")
    print("-"*60)
    be = break_even_analysis(
        price            = 7.99,
        pages            = 200,
        production_cost  = 150,   # cover design + editing
        monthly_ad_spend = 50,    # Amazon Ads budget
    )
    for k, v in be.items():
        print(f"  {k:<30}: {v}")
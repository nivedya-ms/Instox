from decimal import ROUND_HALF_UP, Decimal


def calculate_retail_price(cost_price, profit_percentage):
    """retail = cost * (1 + profit_percentage / 100), rounded to 2dp."""
    cost = Decimal(str(cost_price))
    pct = Decimal(str(profit_percentage))
    retail = cost * (Decimal("1") + pct / Decimal("100"))
    return retail.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_profit(retail_price, cost_price, quantity=1):
    retail = Decimal(str(retail_price))
    cost = Decimal(str(cost_price))
    return ((retail - cost) * Decimal(str(quantity))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

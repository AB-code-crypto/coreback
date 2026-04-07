from decimal import Decimal, ROUND_HALF_UP


def format_decimal_for_admin(value, places: int = 5) -> str:
    if value is None:
        return "—"

    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    quant = Decimal("1").scaleb(-places)
    value = value.quantize(quant, rounding=ROUND_HALF_UP)

    text = format(value, "f")

    if "." in text:
        text = text.rstrip("0").rstrip(".")

    if text in {"-0", "-0.0", ""}:
        return "0"

    return text

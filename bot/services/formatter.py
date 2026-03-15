"""Format peptide comparison results for Telegram using HTML."""

from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import SITE_URL


def build_vendor_url(product: dict) -> str:
    """Build the affiliate URL for a product."""
    vendor = product.get("vendor", {})
    if vendor.get("affiliate_url"):
        return vendor["affiliate_url"]
    base = product.get("product_url") or vendor.get("url", "")
    param = vendor.get("affiliate_param")
    if param and base:
        sep = "&" if "?" in base else ""
        return f"{base}{sep}{param}" if sep else f"{base}{param}"
    return base


def escape_md(text: str) -> str:
    """HTML-escape text for Telegram HTML parse mode."""
    return escape(str(text))


def format_price_message(peptide: dict, products: list[dict]) -> tuple[str, InlineKeyboardMarkup | None]:
    """Format a peptide comparison message with vendor buttons.

    Returns (message_text, keyboard). Uses HTML parse mode.
    """
    name = peptide["name"]
    slug = peptide["slug"]
    category = peptide.get("category", "")

    if not products:
        text = (
            f"<b>{escape_md(name)}</b>\n\n"
            f"No in-stock products found right now.\n"
            f"Check back later or view on the site.\n\n"
            f'<i>Powered by</i> <a href="{SITE_URL}/peptides/{slug}">peptide-compare.com</a>'
        )
        return text, None

    # Group by dosage — find the most common one
    dosage_counts: dict[float, int] = {}
    for p in products:
        qty = p.get("quantity_mg")
        if qty:
            dosage_counts[qty] = dosage_counts.get(qty, 0) + 1

    featured_dose = max(dosage_counts, key=dosage_counts.get) if dosage_counts else None

    # Filter to featured dosage if we have one, otherwise show all
    if featured_dose and len(dosage_counts) > 1:
        dose_products = [p for p in products if p.get("quantity_mg") == featured_dose]
        if len(dose_products) >= 3:
            products = dose_products

    # Build message
    lines = [f"<b>{escape_md(name)}</b>"]
    if category:
        lines.append(f"<i>{escape_md(category)}</i>")
    if featured_dose:
        lines.append(f"Showing {featured_dose}mg")
    lines.append("")

    # Vendor rows
    buttons = []
    coupons = []
    for i, p in enumerate(products[:6]):
        vendor = p.get("vendor", {})
        vname = vendor.get("name", "Unknown")
        price = p.get("price")
        price_per_mg = p.get("price_per_mg")
        rating = vendor.get("finnrick_avg_score")

        price_str = f"${price:.2f}" if price else "N/A"
        ppm_str = f" (${price_per_mg:.2f}/mg)" if price_per_mg else ""
        rating_str = f" | {rating:.1f}/10" if rating else ""

        lines.append(f"{escape_md(vname)} — <b>{price_str}</b>{ppm_str}{rating_str}")

        # Vendor link button
        url = build_vendor_url(p)
        if url:
            buttons.append([InlineKeyboardButton(f"Buy from {vname} — {price_str}", url=url)])

        # Collect coupon info
        if vendor.get("coupon_code"):
            desc = vendor.get("coupon_description", "")
            desc_str = f" ({desc})" if desc else ""
            coupons.append(f"<code>{escape_md(vendor['coupon_code'])}</code>{escape_md(desc_str)} at {escape_md(vname)}")

    # Coupon section
    if coupons:
        lines.append("")
        lines.append("<b>Coupons:</b>")
        for c in coupons:
            lines.append(f"  {c}")

    # Footer
    lines.append("")
    lines.append(f'<i>Powered by</i> <a href="{SITE_URL}/peptides/{slug}">peptide-compare.com</a>')

    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    return "\n".join(lines), keyboard

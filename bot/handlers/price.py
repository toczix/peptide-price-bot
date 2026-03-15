"""Core handler — matches peptide names and returns price comparisons."""

import asyncio
import logging
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.db import PeptideDB
from bot.services.matcher import PeptideMatcher
from bot.services.formatter import format_price_message, escape_md
from bot.services import llm

logger = logging.getLogger(__name__)

SEARCH_MESSAGES = [
    "Searching {count} vendors for <b>{name}</b>...",
    "Finding the best prices on <b>{name}</b> across {count} vendors...",
    "Looking up <b>{name}</b> across {count} vendors...",
]


def create_handler(db: PeptideDB, matcher: PeptideMatcher):
    """Create the message handler with injected dependencies."""

    # Count enabled vendors once for the loading message
    vendor_count = "50+"

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if not text:
            return

        # Try to match a peptide
        peptide, confidence = matcher.match(text)

        if confidence >= 85:
            # High confidence — show dosage picker
            await show_dosage_picker(update, db, peptide, vendor_count)

        elif confidence >= 65:
            # Medium confidence — ask for confirmation
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        f"Yes, show {peptide['name']}",
                        callback_data=f"pick:{peptide['id']}",
                    ),
                    InlineKeyboardButton("No", callback_data="cancel"),
                ]
            ])
            await update.message.reply_text(
                f"Did you mean <b>{escape_md(peptide['name'])}</b>?",
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        else:
            # No peptide match — use LLM for general Q&A
            try:
                response = await llm.chat(text)
                await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"LLM error: {e}")
                await update.message.reply_text(
                    "I couldn't find a peptide with that name. "
                    "Try typing the full name like 'BPC-157' or 'semaglutide'."
                )

        # Log the query
        log_query(update, text, peptide, confidence)

    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "cancel":
            await query.edit_message_text("No problem. Type another peptide name to search.")
            return

        # "pick:{peptide_id}" — show dosage picker
        if data.startswith("pick:"):
            peptide_id = data.split(":", 1)[1]
            peptide = next((p for p in db.peptides if p["id"] == peptide_id), None)
            if peptide:
                await show_dosage_picker_edit(query, db, peptide, vendor_count)
            else:
                await query.edit_message_text("Peptide not found. Try again.")
            return

        # "dose:{peptide_id}:{mg}" — show results for specific dose
        if data.startswith("dose:"):
            parts = data.split(":", 2)
            peptide_id, dose_mg = parts[1], float(parts[2])
            peptide = next((p for p in db.peptides if p["id"] == peptide_id), None)
            if peptide:
                await show_results_with_loading(query, db, peptide, vendor_count, dose_mg)
            return

        # "all:{peptide_id}" — show all dosages
        if data.startswith("all:"):
            peptide_id = data.split(":", 1)[1]
            peptide = next((p for p in db.peptides if p["id"] == peptide_id), None)
            if peptide:
                await show_results_with_loading(query, db, peptide, vendor_count, None)
            return

    return handle_message, handle_callback


async def show_dosage_picker(update, db: PeptideDB, peptide: dict, vendor_count: str):
    """Show available dosages as inline buttons."""
    dosages = db.get_dosages(peptide["id"])

    if not dosages:
        # No products found — show empty result
        msg = await update.message.reply_text(
            f"Searching {vendor_count} vendors for <b>{escape_md(peptide['name'])}</b>...",
            parse_mode="HTML",
        )
        await asyncio.sleep(1.5)
        text, keyboard = format_price_message(peptide, [])
        await msg.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    if len(dosages) == 1:
        # Only one dosage — skip picker, go straight to results
        msg = await update.message.reply_text(
            f"Searching {vendor_count} vendors for <b>{escape_md(peptide['name'])}</b>...",
            parse_mode="HTML",
        )
        await asyncio.sleep(2)
        products = db.get_products_by_dose(peptide["id"], dosages[0]["mg"])
        text, keyboard = format_price_message(peptide, products)
        await msg.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        return

    # Multiple dosages — show picker
    buttons = []
    for d in dosages[:5]:
        label = f"{d['mg']}mg ({d['vendors']} vendor{'s' if d['vendors'] != 1 else ''})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dose:{peptide['id']}:{d['mg']}")])

    buttons.append([InlineKeyboardButton("Show all dosages", callback_data=f"all:{peptide['id']}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"<b>{escape_md(peptide['name'])}</b>\n\n"
        f"Which dosage are you looking for?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def show_dosage_picker_edit(query, db: PeptideDB, peptide: dict, vendor_count: str):
    """Same as show_dosage_picker but edits existing message."""
    dosages = db.get_dosages(peptide["id"])

    if not dosages or len(dosages) == 1:
        await show_results_with_loading(query, db, peptide, vendor_count, dosages[0]["mg"] if dosages else None)
        return

    buttons = []
    for d in dosages[:5]:
        label = f"{d['mg']}mg ({d['vendors']} vendor{'s' if d['vendors'] != 1 else ''})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dose:{peptide['id']}:{d['mg']}")])

    buttons.append([InlineKeyboardButton("Show all dosages", callback_data=f"all:{peptide['id']}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        f"<b>{escape_md(peptide['name'])}</b>\n\n"
        f"Which dosage are you looking for?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def show_results_with_loading(query, db: PeptideDB, peptide: dict, vendor_count: str, dose_mg: float | None):
    """Show a loading message, then edit it with results."""
    # Show loading
    await query.edit_message_text(
        f"Searching {vendor_count} vendors for <b>{escape_md(peptide['name'])}</b>"
        + (f" {dose_mg}mg" if dose_mg else "")
        + "...",
        parse_mode="HTML",
    )

    await asyncio.sleep(2)

    # Fetch results
    if dose_mg:
        products = db.get_products_by_dose(peptide["id"], dose_mg)
    else:
        products = db.get_products(peptide["id"])

    text, keyboard = format_price_message(peptide, products)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


def log_query(update: Update, text: str, peptide: dict | None, confidence: float):
    """Append query to click log for analytics."""
    try:
        user = update.effective_user
        entry = (
            f"{datetime.now(timezone.utc).isoformat()}\t"
            f"{user.id}\t"
            f"{user.username or 'anon'}\t"
            f"{text}\t"
            f"{peptide['name'] if peptide else 'none'}\t"
            f"{confidence:.0f}\n"
        )
        with open("queries.log", "a") as f:
            f.write(entry)
    except Exception:
        pass

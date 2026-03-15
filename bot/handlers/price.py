"""Core handler — matches peptide names and returns price comparisons."""

import logging
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.db import PeptideDB
from bot.services.matcher import PeptideMatcher
from bot.services.formatter import format_price_message, escape_md
from bot.services import llm

logger = logging.getLogger(__name__)


def create_handler(db: PeptideDB, matcher: PeptideMatcher):
    """Create the message handler with injected dependencies."""

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if not text:
            return

        # Try to match a peptide
        peptide, confidence = matcher.match(text)

        if confidence >= 85:
            # High confidence — show results
            await show_results(update, db, peptide)

        elif confidence >= 65:
            # Medium confidence — ask for confirmation
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        f"Yes, show {peptide['name']}",
                        callback_data=f"show:{peptide['id']}",
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

        if query.data == "cancel":
            await query.edit_message_text("No problem. Type another peptide name to search.")
            return

        if query.data.startswith("show:"):
            peptide_id = query.data.split(":", 1)[1]
            # Find peptide by ID
            peptide = next((p for p in db.peptides if p["id"] == peptide_id), None)
            if peptide:
                await show_results_edit(query, db, peptide)
            else:
                await query.edit_message_text("Peptide not found. Try again.")

    return handle_message, handle_callback


async def show_results(update: Update, db: PeptideDB, peptide: dict):
    """Fetch products and send the formatted comparison."""
    products = db.get_products(peptide["id"])
    text, keyboard = format_price_message(peptide, products)
    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=keyboard
    )


async def show_results_edit(query, db: PeptideDB, peptide: dict):
    """Same as show_results but edits the existing message (for callbacks)."""
    products = db.get_products(peptide["id"])
    text, keyboard = format_price_message(peptide, products)
    await query.edit_message_text(
        text, parse_mode="HTML", reply_markup=keyboard
    )


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

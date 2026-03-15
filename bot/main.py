"""Entry point for the Peptide Compare Telegram bot."""

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_ANON_KEY
from bot.services.db import PeptideDB
from bot.services.matcher import PeptideMatcher
from bot.handlers.start import start, help_cmd
from bot.handlers.price import create_handler

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    # Initialize database and matcher
    db = PeptideDB(SUPABASE_URL, SUPABASE_ANON_KEY)
    db.load_peptides()
    matcher = PeptideMatcher(db.peptides)

    # Create handlers with dependencies
    handle_message, handle_callback = create_handler(db, matcher)

    # Build application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers (order matters — commands first)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting — polling for updates")
    app.run_polling()


if __name__ == "__main__":
    main()

"""Start and help command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

WELCOME = (
    "Welcome to Peptide Compare Bot!\n\n"
    "I help you find the best peptide prices across 50+ vendors with real-time data.\n\n"
    "How to use:\n"
    "  Just type a peptide name like:\n"
    "  BPC-157\n"
    "  semaglutide\n"
    "  retatrutide\n"
    "  tirzepatide\n\n"
    "I'll show you the cheapest in-stock options with direct links.\n\n"
    "You can also ask me general questions about peptides.\n\n"
    "Powered by peptide-compare.com"
)

HELP = (
    "Peptide Compare Bot — Help\n\n"
    "Commands:\n"
    "  /start — Welcome message\n"
    "  /help — This message\n\n"
    "Usage:\n"
    "  Type any peptide name to compare prices.\n"
    "  Type a question to get peptide info.\n\n"
    "Examples:\n"
    "  BPC-157\n"
    "  semaglutide\n"
    "  what does TB-500 do?\n"
    "  best peptide for recovery\n\n"
    "Data updates 3x/week from 50+ vendors.\n"
    "peptide-compare.com"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)

import os
import logging
import requests
import re
import telegram
from flask import Flask, request
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Basic Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variable for the token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")


# --- Core Logic Function ---

async def process_url(url: str, update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """The main function to process a URL and send the direct link back."""
    message = await update.message.reply_text("🔗 Link detected. Navigating the website, please wait...")

    # Get the direct link
    from downloader import get_dropgalaxy_link
    final_link, error = get_dropgalaxy_link(url)

    if error:
        await message.edit_text(f"❌ Error: {error}")
        return

    # *** THIS IS THE KEY CHANGE ***
    # Instead of downloading, we send the link back to the user.
    if final_link:
        # Prepare a nice-looking message with a clickable link
        # Note: We escape characters for MarkdownV2
        escaped_link = final_link.replace('.', r'\.').replace('-', r'\-').replace('(', r'\(').replace(')', r'\)')
        reply_text = (
            f"✅ *Success\\!* \n\n"
            f"I have found the direct download link for you\\.\n\n"
            f"➡️ [Click Here to Download]({escaped_link})\n\n"
            f"_(This link will start the download in your browser\\.)_"
        )
        # Use MarkdownV2 for formatting
        await message.edit_text(
            text=reply_text,
            parse_mode=telegram.constants.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )
    else:
        await message.edit_text("Could not find the final download link. The site may have changed.")


# --- Handlers (No changes needed, but included for completeness) ---

async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text("Hi! Send me a DropGalaxy link (or use /download <link>) and I will get the direct download link for you.")

async def download_command_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /download command."""
    if not context.args:
        await update.message.reply_text("Please provide a URL after the /download command.")
        return
    await process_url(context.args[0], update, context)

async def plain_message_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles plain text messages containing a link."""
    if update.message and update.message.text and ('dgdrive.site' in update.message.text or 'dropgalaxy' in update.message.text):
        await process_url(update.message.text, update, context)
    else:
        await update.message.reply_text("This does not look like a DropGalaxy link.")


# --- Flask App and Bot Initialization (No changes needed) ---
application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("download", download_command_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_message_handler))

app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook_handler():
    update = telegram.Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Hello! I am the DropGalaxy downloader bot. I am alive!"
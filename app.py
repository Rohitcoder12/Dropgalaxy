import os
import logging
import asyncio
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

# --- Core Logic ---
# (No changes needed in this part)
async def process_url(url: str, update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    from downloader import get_dropgalaxy_link
    message = await update.message.reply_text("🔗 Link detected. Processing, please wait...")
    final_link, error = get_dropgalaxy_link(url)
    if error:
        await message.edit_text(f"❌ Error: {error}")
        return
    if final_link:
        await message.edit_text(f"✅ Success! Found direct link. Now downloading...")
        await download_file_and_send(final_link, update.message.chat_id, context, message)
    else:
        await message.edit_text("Could not find the final download link.")

async def download_file_and_send(url: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, status_message: telegram.Message):
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            filename = url.split('/')[-1] or "downloaded_file"
            if 'content-disposition' in r.headers:
                fn = re.findall("filename=\"(.+)\"", r.headers['content-disposition'])
                if fn:
                    filename = fn[0]
            await status_message.edit_text(f"Uploading '{filename}' to Telegram...")
            await context.bot.send_document(chat_id=chat_id, document=r.content, filename=filename, read_timeout=120, write_timeout=120)
        await status_message.delete()
    except Exception as e:
        logger.error(f"CRASH in download_file_and_send: {e}", exc_info=True)
        await status_message.edit_text(f"❌ An error occurred while sending the file: {e}")

# --- Handlers ---
async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a DropGalaxy link (or use /download <link>).")

async def download_command_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a URL after the /download command.")
        return
    await process_url(context.args[0], update, context)

async def plain_message_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text and ('dgdrive.site' in update.message.text or 'dropgalaxy' in update.message.text):
        await process_url(update.message.text, update, context)
    else:
        await update.message.reply_text("This does not look like a DropGalaxy link.")

# --- The CRITICAL FIX IS HERE ---

# Create the Application object
application = Application.builder().token(TOKEN).build()

# Add all the handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("download", download_command_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_message_handler))

# Run the bot in a separate thread
asyncio.create_task(application.run_polling())

# Initialize Flask app
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook_handler():
    # This now just confirms the webhook is being called
    logger.info("Webhook received!")
    return "ok"

@app.route("/")
def index():
    return "Hello! I am the DropGalaxy downloader bot. I am alive!"
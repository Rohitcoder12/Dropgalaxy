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
    """The main function to process a URL, get the link, and send the file."""
    message = await update.message.reply_text("🔗 Link detected. Processing, please wait...")

    # Get the direct link
    from downloader import get_dropgalaxy_link # Import here to avoid issues
    final_link, error = get_dropgalaxy_link(url)

    if error:
        await message.edit_text(f"❌ Error: {error}")
        return

    if final_link:
        await message.edit_text(f"✅ Success! Found direct link. Now downloading and uploading to Telegram. This may take a while...")
        await download_file_and_send(final_link, update.message.chat_id, context, message)
    else:
        await message.edit_text("Could not find the final download link. The site may have changed.")


async def download_file_and_send(url: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, status_message: telegram.Message):
    """Downloads a file and sends it as a document to Telegram."""
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            filename = "downloaded_file"
            if 'content-disposition' in r.headers:
                disposition = r.headers['content-disposition']
                fn = re.findall("filename=\"(.+)\"", disposition)
                if fn:
                    filename = fn[0]
            else:
                filename = url.split('/')[-1] or filename

            await status_message.edit_text(f"Uploading '{filename}' to Telegram...")
            await context.bot.send_document(chat_id=chat_id, document=r.content, filename=filename, read_timeout=60, write_timeout=60)
        await status_message.delete()
    except Exception as e:
        logger.error(f"Failed to download or send file: {e}")
        await status_message.edit_text(f"❌ An error occurred while sending the file: {e}")


# --- Telegram Bot Handler Functions ---

async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text("Hi! Send me a DropGalaxy link (or use /download <link>) and I will try to get the file for you.")

async def download_command_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /download command."""
    if not context.args:
        await update.message.reply_text("Please provide a URL after the /download command.")
        return
    url = context.args[0]
    await process_url(url, update, context)

async def plain_message_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles plain text messages containing a link."""
    if not update.message or not update.message.text:
        return
    url = update.message.text
    if 'dgdrive.site' in url or 'dropgalaxy' in url:
        await process_url(url, update, context)
    else:
        await update.message.reply_text("This does not look like a valid DropGalaxy link. Please send a link from dgdrive.site.")


# --- Flask App and Bot Initialization ---

# Initialize the Application
application = Application.builder().token(TOKEN).build()

# Add all the handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("download", download_command_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_message_handler))

# Initialize Flask app
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook_handler():
    """Parses the request and handles the update."""
    await application.update_queue.put(
        telegram.Update.de_json(request.get_json(force=True), application.bot)
    )
    return "ok"

@app.route("/")
def index():
    """A simple health check page."""
    return "Hello! I am the DropGalaxy downloader bot. I am alive!"
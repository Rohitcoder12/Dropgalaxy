import os
import logging
import requests
import telegram
from flask import Flask, request, jsonify
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    filters,
    Dispatcher
)
from downloader import get_dropgalaxy_link

# --- Basic Setup ---
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
APP_URL = os.environ.get("RENDER_EXTERNAL_URL") # Render provides this automatically

if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")
if not APP_URL:
    raise ValueError("No RENDER_EXTERNAL_URL found. Please set this in Render's environment.")


# --- Telegram Bot Handler Functions ---

def start(update: telegram.Update, context: telegram.ext.CallbackContext):
    """Sends a help message when the /start command is issued."""
    update.message.reply_text("Hi! Send me a DropGalaxy link and I will try to download the file for you.")

def handle_message(update: telegram.Update, context: telegram.ext.CallbackContext):
    """Handles any message that contains a potential DropGalaxy link."""
    url = update.message.text
    if 'dgdrive.site' in url or 'dropgalaxy' in url:
        message = update.message.reply_text("🔗 Link detected. Processing, please wait...")

        # Get the direct link
        final_link, error = get_dropgalaxy_link(url)

        if error:
            message.edit_text(f"❌ Error: {error}")
            return

        if final_link:
            message.edit_text(f"✅ Success! Found direct link. Now downloading and uploading to Telegram. This may take a while...")
            # Download the file from the direct link and send it to the user
            download_file_and_send(final_link, update.message.chat_id, context, message)
        else:
            message.edit_text("Could not find the final download link. The site may have changed.")
    else:
        update.message.reply_text("Please send a valid DropGalaxy link.")


def download_file_and_send(url: str, chat_id: int, context: telegram.ext.CallbackContext, status_message: telegram.Message):
    """Downloads a file and sends it as a document to Telegram."""
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            # Try to get the filename from headers, otherwise guess from URL
            if 'content-disposition' in r.headers:
                filename = re.findall("filename=\"(.+)\"", r.headers['content-disposition'])[0]
            else:
                filename = url.split('/')[-1]

            status_message.edit_text(f"Uploading '{filename}' to Telegram...")
            context.bot.send_document(chat_id=chat_id, document=r.content, filename=filename, timeout=50)
        status_message.delete() # Clean up the status message after sending the file
    except Exception as e:
        logger.error(f"Failed to download or send file: {e}")
        status_message.edit_text(f"❌ An error occurred while sending the file: {e}")


# --- Flask App and Bot Initialization ---

# Initialize Flask app
app = Flask(__name__)

# Initialize Bot and Dispatcher
bot = telegram.Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=4, use_context=True)

# Register handlers with the dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# This is the single webhook route that Telegram will call
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook_handler():
    """Handles webhook requests from Telegram."""
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# This route is used to set the webhook
@app.route("/set_webhook", methods=['GET', 'POST'])
def setup_webhook():
    """Sets the webhook on Telegram to point to this app."""
    webhook_url = f"{APP_URL}/{TOKEN}"
    success = bot.set_webhook(webhook_url)
    if success:
        return f"Webhook set to {webhook_url}"
    else:
        return "Webhook setup failed."

# This is a health check route for Render
@app.route("/")
def index():
    """A simple health check page."""
    return "Hello! I am the DropGalaxy downloader bot. I am alive!"
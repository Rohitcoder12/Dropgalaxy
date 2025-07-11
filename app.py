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
    logger.info(f"Starting to process URL: {url}")
    message = await update.message.reply_text("🔗 Link detected. Processing, please wait...")

    # Get the direct link
    from downloader import get_dropgalaxy_link # Import here to avoid issues
    final_link, error = get_dropgalaxy_link(url)

    if error:
        logger.error(f"Error from get_dropgalaxy_link: {error}")
        await message.edit_text(f"❌ Error: {error}")
        return

    if final_link:
        logger.info(f"Found direct link: {final_link}")
        await message.edit_text(f"✅ Success! Found direct link. Now downloading and uploading to Telegram. This may take a while...")
        await download_file_and_send(final_link, update.message.chat_id, context, message)
    else:
        logger.warning("get_dropgalaxy_link returned no link and no error.")
        await message.edit_text("Could not find the final download link. The site may have changed.")


async def download_file_and_send(url: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE, status_message: telegram.Message):
    """Downloads a file and sends it as a document to Telegram."""
    logger.info(f"Starting download_file_and_send for URL: {url}")
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            logger.info("Successfully started streaming from direct link.")
            filename = "downloaded_file"
            if 'content-disposition' in r.headers:
                disposition = r.headers['content-disposition']
                fn = re.findall("filename=\"(.+)\"", disposition)
                if fn:
                    filename = fn[0]
            else:
                filename = url.split('/')[-1] or filename
            
            logger.info(f"Determined filename: {filename}. Now uploading to Telegram.")
            await status_message.edit_text(f"Uploading '{filename}' to Telegram...")
            await context.bot.send_document(chat_id=chat_id, document=r.content, filename=filename, read_timeout=60, write_timeout=60)
            logger.info("Successfully sent document to Telegram.")
        await status_message.delete()
    except Exception as e:
        logger.error(f"CRASH in download_file_and_send: {e}", exc_info=True)
        await status_message.edit_text(f"❌ An error occurred while sending the file: {e}")


# --- Telegram Bot Handler Functions ---

async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received /start command.")
    await update.message.reply_text("Hi! Send me a DropGalaxy link (or use /download <link>) and I will try to get the file for you.")

async def download_command_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received /download command.")
    if not context.args:
        await update.message.reply_text("Please provide a URL after the /download command.")
        return
    url = context.args[0]
    await process_url(url, update, context)

async def plain_message_handler(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received a plain text message.")
    if not update.message or not update.message.text:
        logger.warning("Plain message handler received an update with no text.")
        return
    url = update.message.text
    if 'dgdrive.site' in url or 'dropgalaxy' in url:
        logger.info("Message contains a valid link, processing...")
        await process_url(url, update, context)
    else:
        logger.info("Message does not contain a valid link.")
        await update.message.reply_text("This does not look like a valid DropGalaxy link. Please send a link from dgdrive.site.")


# --- Flask App and Bot Initialization ---
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("download", download_command_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_message_handler))
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook_handler():
    """Parses the request and handles the update."""
    logger.info("Webhook received!")
    update = telegram.Update.de_json(request.get_json(force=True), application.bot)
    # The key fix is to use the update_queue for webhook integration
    await application.update_queue.put(update)
    logger.info("Webhook processing finished.")
    return "ok"

@app.route("/")
def index():
    """A simple health check page that you can visit in your browser."""
    return "Hello! I am the DropGalaxy downloader bot. I am alive!"
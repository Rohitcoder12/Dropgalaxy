from flask import Flask, request, jsonify
from downloader import get_dropgalaxy_link
import os
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, filters  # Corrected import
import logging

app = Flask(__name__)

# Telegram Bot Token (from environment variable)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# --- Telegram Bot Handlers ---

def start(update, context):
    """Sends a help message when the /start command is issued."""
    update.message.reply_text('Hi! Send me a DropGalaxy link to download the file.')

def download_handler(update, context):
    """Handles the /download command and downloads the file."""
    try:
        dropgalaxy_url = update.message.text.replace('/download ', '')  # Extract URL
        if not dropgalaxy_url:
            update.message.reply_text("Please provide a DropGalaxy link after the /download command.")
            return

        final_link, error = get_dropgalaxy_link(dropgalaxy_url)

        if error:
            update.message.reply_text(f"Error: {error}")
            return

        if final_link:
            update.message.reply_text(f"Downloading from: {final_link}")
            # Download the file and send it to the user
            download_file_and_send(final_link, update.message.chat_id, context)
        else:
            update.message.reply_text("Could not find the download link.")

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        update.message.reply_text("An unexpected error occurred. Please try again later.")

def download_file_and_send(url, chat_id, context):
    """Downloads a file from a URL and sends it to a Telegram chat."""
    import requests
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        filename = url.split('/')[-1]
        
        # Send the file to Telegram
        context.bot.send_document(chat_id=chat_id, document=response.content, filename=filename)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {e}")
        context.bot.send_message(chat_id=chat_id, text=f"Error downloading file: {e}")
    except Exception as e:
        logger.exception(f"An error occurred while sending the file: {e}")
        context.bot.send_message(chat_id=chat_id, text="An error occurred while sending the file.")

def echo(update, context):
    """Echoes the user's message."""
    update.message.reply_text(update.message.text)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

# --- Flask Routes ---

@app.route('/', methods=['POST'])
def telegram_webhook():
    """Handles Telegram webhook requests."""
    # Get the update from the request
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    # Dispatch the update to the handler
    dispatcher.process_update(update)
    return jsonify({'status': 'OK'})

if __name__ == '__main__':
    # --- Telegram Bot Setup ---
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Register handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("download", download_handler))
    dp.add_handler(MessageHandler(filters.text & ~filters.command, echo))  # Corrected import
    dp.add_error_handler(error)

    # Start the bot
    updater.start_webhook(listen="0.0.0.0", port=int(os.environ.get('PORT', 5000)), webhook_url=f"YOUR_RENDER_APP_URL/{TELEGRAM_BOT_TOKEN}")
    # Start the Flask app
    app.run(debug=True)
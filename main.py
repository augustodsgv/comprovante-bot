import os
import sys
from enum import Enum, auto
import logging

from telegram import Update, File
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import boto3

LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR").upper()
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

# Create handler that logs to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(LOG_LEVEL)
logger.addHandler(handler)

logger.error(f"Log level set to {LOG_LEVEL}")


try:
    TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
    S3_ACCESS_KEY_ID = os.environ["S3_ACCESS_KEY_ID"]
    S3_SECRET_ACCESS_KEY = os.environ["S3_SECRET_ACCESS_KEY"]
    S3_ENDPOINT_URL = os.environ["S3_ENDPOINT_URL"]
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "comprovante-bot")

except KeyError:
    logger.error("Error: Missing environment variable")
    sys.exit(1)

temp_user_data = dict()


class ReceiptsStates(Enum):
    ASK_TYPE = auto()
    ASK_MONTH = auto()
    ASK_FILE = auto()


AVAILABLE_TYPES = ("agua", "luz", "aluguel", "condominio", "internet")

YEAR = 2025  # Hard coded for now
MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

SUPPORTED_DOCS_EXT = "pdf"
SUPPORTED_IMG_EXT = ("png", "jpg", "jpeg")


# 1 - Receive /comprovante call
async def start_receipts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles "comprovante" command. Basically sets a user state for knowing when the next file sent is a receipts
    """
    user_id = update.effective_user.id
    logger.info(f'User "{user_id}" started sending a receipt.')

    temp_user_data[user_id] = dict()
    await update.message.reply_text("Comprovante de qual conta você deseja guardar?")
    await update.message.reply_text(f"Tipos disponíveis: {', '.join(AVAILABLE_TYPES)}")
    return ReceiptsStates.ASK_TYPE


# 2 - Ask receipts type
async def receive_receipts_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receives and checks the type of the receipts
    """
    user_id = update.effective_user.id

    # Check type
    receipts_type = update.message.text
    if receipts_type.lower() not in AVAILABLE_TYPES:
        await update.message.reply_text(f'Tipo "{receipts_type}" inválido')
        await update.message.reply_text(
            f"Tipos disponíveis: {', '.join(AVAILABLE_TYPES)}"
        )
        logger.warning(
            f'User "{user_id}" choosed an undefined receipt type "{receipts_type}".'
        )

        return ReceiptsStates.ASK_TYPE

    temp_user_data[user_id]["receipts_type"] = receipts_type.lower()
    logger.info(
        f'User "{user_id}" choosed sending a "{receipts_type.lower()}" receipt.'
    )

    await update.message.reply_text("De qual mês é o comprovante?")
    return ReceiptsStates.ASK_MONTH


# 3 - Ask receipts month
async def receive_receipts_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receives and checks the month of the receipts.
    """
    # Check type
    receipts_month = update.message.text
    if receipts_month.lower() not in MONTHS:
        await update.message.reply_text(f'Mês "{receipts_month}" inválido')
        await update.message.reply_text(f"Meses disponíveis: {', '.join(MONTHS)}")
        logger.warning(
            f'User "{user_id}" choosed an undefined month type "{receipts_month}".'
        )
        return ReceiptsStates.ASK_MONTH

    user_id = update.effective_user.id
    temp_user_data[user_id]["receipts_month"] = receipts_month.lower()
    logger.info(
        f'User "{user_id}" choosed sending a receipt from "{receipts_month.lower()}"'
    )

    await update.message.reply_text("Envie o arquivo de comprovante.")
    return ReceiptsStates.ASK_FILE


# 4 - Ask receipts month
async def receive_receipts_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receives a receipt sent to the bot.
    All files are placed under BASE_DOWNLOAD_DIR, inside a folder names <month>-<year>
    """
    # Getting general data
    user_id = update.effective_user.id
    receipt_type = temp_user_data[user_id]["receipts_type"]
    receipt_month = temp_user_data[user_id]["receipts_month"]

    # Treating documents (i.e. pdf)
    if update.message.document:
        document = update.message.document

        # Checking file extenstion
        user_file_name = document.file_name
        file_extension = user_file_name.split(".")[-1]
        if file_extension not in SUPPORTED_DOCS_EXT:
            await update.message.reply_text("Este documento não tem um formato válido.")
            await update.message.reply_text(
                f"Formatos válidos: {', '.join(SUPPORTED_DOCS_EXT)}"
            )
            logger.warning(
                f'User "{user_id}" sent an unprocessable file "{user_file_name}".'
            )

            return ReceiptsStates.ASK_FILE
        telegram_file: File = await context.bot.get_file(document.file_id)

    # Treating images
    if update.message.photo:
        photo = update.message.photo[-1]
        telegram_file: File = await context.bot.get_file(photo.file_id)
        file_extension = "jpg"

    # Uploading to S3
    s3_object_name = (
        f"comprovante-{receipt_type}-{receipt_month}-{YEAR}-{file_extension}"
    )
    temp_file_name = f"{receipt_type}-{receipt_month}-{YEAR}.temp"
    await telegram_file.download_to_drive(
        temp_file_name
    )  # Downloading to temporary file
    upload_to_s3(temp_file_name, s3_object_name)
    logger.info(f"Successfully update {s3_object_name} to s3")

    await update.message.reply_text(f"Comprovante salvo com sucesso.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancels receipts upload
    """
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END


def upload_to_s3(file_name: str, s3_object_name: str) -> None:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        endpoint_url=S3_ENDPOINT_URL,
    )

    """
    I don't know why, but if we don't have this functions here boto3 throws this error:
    "... An error occurred (AccessDenied) when calling the PutObject operation: Credentials or specified url is malformed..."
    TODO: try fix it
    """
    s3_client.list_buckets()

    response = s3_client.upload_file(file_name, S3_BUCKET_NAME, s3_object_name)
    logging.debug(response)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    receipts_handler = ConversationHandler(
        entry_points=[CommandHandler("receipts", start_receipts)],
        states={
            ReceiptsStates.ASK_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_receipts_type)
            ],
            ReceiptsStates.ASK_MONTH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_receipts_month)
            ],
            ReceiptsStates.ASK_FILE: [
                MessageHandler(
                    filters.Document.ALL | filters.PHOTO, receive_receipts_file
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(receipts_handler)
    app.run_polling()


if __name__ == "__main__":
    main()

from telegram import (
    Update,
    File
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
import os
from enum import Enum, auto

TOKEN = os.environ['TELEGRAM_TOKEN']
BASE_DOWNLOAD_DIR = os.getenv('BASE_DOWNLOAD_DIR', 'temp_downloads')

temp_user_data = dict()

class ReceiptsStates (Enum):
    ASK_TYPE = auto()
    ASK_MONTH = auto()
    ASK_FILE = auto()

AVAILABLE_TYPES = ('agua', 'luz', 'aluguel', 'condominio', 'internet')

YEAR = 2025     # Hard coded for now
MONTHS = (
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
)

SUPPORTED_DOCS_EXT = ('pdf')
SUPPORTED_IMG_EXT = ('png', 'jpg', 'jpeg')

# 1 - Receive /comprovante call
async def start_receipts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles "comprovante" command. Basically sets a user state for knowing when the next file sent is a receipts
    """
    user_id = update.effective_user.id
    temp_user_data[user_id] = dict()
    await update.message.reply_text("Comprovante de qual conta você deseja guardar?")
    await update.message.reply_text(f"Tipos disponíveis: {', '.join(AVAILABLE_TYPES)}")
    return ReceiptsStates.ASK_TYPE

# 2 - Ask receipts type
async def receive_receipts_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receives and checks the type of the receipts
    """
    # Check type
    receipts_type = update.message.text
    if receipts_type.lower() not in AVAILABLE_TYPES:
        await update.message.reply_text(f"Tipo \"{receipts_type}\" inválido")
        await update.message.reply_text(f"Tipos disponíveis: {', '.join(AVAILABLE_TYPES)}")
        return ReceiptsStates.ASK_TYPE

    user_id = update.effective_user.id
    print(receipts_type)
    temp_user_data[user_id]['receipts_type'] = receipts_type.lower()
    print(temp_user_data[user_id]['receipts_type'])
    await update.message.reply_text("De qual mês é o receipts?")
    return ReceiptsStates.ASK_MONTH

# 3 - Ask receipts month
async def receive_receipts_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receives and checks the month of the receipts. 
    """
    # Check type
    receipts_month = update.message.text
    if receipts_month.lower() not in MONTHS:
        await update.message.reply_text(f"Mês \"{receipts_month}\" inválido")
        await update.message.reply_text(f"Meses disponíveis: {', '.join(MONTHS)}")
        return ReceiptsStates.ASK_MONTH

    user_id = update.effective_user.id
    temp_user_data[user_id]['receipts_month'] = receipts_month.lower()
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
    comp_type = temp_user_data[user_id]['receipts_type']
    comp_month = temp_user_data[user_id]['receipts_month']

    # Treating documents (i.e. pdf)
    if update.message.document:
        document = update.message.document

        # Checking file extenstion
        user_file_name = document.file_name
        file_extension = user_file_name.split('.')[-1]
        if file_extension not in SUPPORTED_DOCS_EXT:
            await update.message.reply_text("Este documento não tem um formato válido.") 
            await update.message.reply_text(f"Formatos válidos: {', '.join(SUPPORTED_DOCS_EXT)}")
            return ReceiptsStates.ASK_FILE
        telegram_file: File = await context.bot.get_file(document.file_id)
    
    # Treating images
    if update.message.photo:
        photo = update.message.photo[-1]
        telegram_file: File = await context.bot.get_file(photo.file_id)
        file_extension = 'jpg'

    # Configuring file name and directory. Directory are based on month and year
    system_file_name = f'comprovante-{comp_type}-{comp_month}.{file_extension}'
    dir_path = f'{BASE_DOWNLOAD_DIR}/{comp_month}-{YEAR}'
    os.makedirs(dir_path, exist_ok=True)       # Creating directory, if not exists

    # Downloading file
    file_path = f'{dir_path}/{system_file_name}'
    await telegram_file.download_to_drive(file_path)

    await update.message.reply_text(f"Comprovante salvo com sucesso.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancels receipts upload
    """
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

# async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     Lists files 
#     """


def main():
    app = Application.builder().token(TOKEN).build()

    # Receipts
    receipts_handler = ConversationHandler(
        entry_points = [CommandHandler("receipts", start_receipts)],
        states = {
            ReceiptsStates.ASK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_receipts_type)],
            ReceiptsStates.ASK_MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_receipts_month)],
            ReceiptsStates.ASK_FILE: [MessageHandler(filters.Document.ALL | filters.PHOTO, receive_receipts_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(receipts_handler)
    
    app.run_polling()

if __name__ == '__main__':
    main()
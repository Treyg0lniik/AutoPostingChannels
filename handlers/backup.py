# handlers/backup.py
import os
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import config

# Ваш Telegram‑username без '@'
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Проверяем, что команда идёт от админа
    if user.username != ADMIN_USERNAME:
        return await update.message.reply_text("❌ Доступ запрещён.")
    # Берём путь к вашему основному файлу с данными
    path = config.DATA_FILE
    if not os.path.exists(path):
        return await update.message.reply_text(f"❌ Файл `{os.path.basename(path)}` не найден.", parse_mode="MarkdownV2")
    # Отправляем в личку
    await context.bot.send_document(
        chat_id=user.id,
        document=open(path, "rb"),
        filename=os.path.basename(path),
        caption=f"📦 Бекап `{os.path.basename(path)}`",
        parse_mode="MarkdownV2"
    )

def register_backup(app):
    app.add_handler(CommandHandler("backup", cmd_backup))

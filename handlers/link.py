from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from storage.storage import Storage

# /link @channel - привязка канала в групповом чате
async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if len(context.args) != 1:
        return await update.message.reply_text('Использование: /link @channel')
    channel = context.args[0]

    # Проверяем, что пользователь админ канала
    try:
        member = await context.bot.get_chat_member(channel, user_id)
    except Exception:
        return await update.message.reply_text('Не удалось получить информацию о канале.')
    if member.status not in ('creator', 'administrator'):
        return await update.message.reply_text('Вы должны быть админом этого канала.')

    # Проверяем существующий binding
    owner = Storage.get_owner(chat_id)
    if owner:
        if owner != user_id:
            return await update.message.reply_text('К этому чату уже привязан канал. Только владелец может изменить его.')
        # Владелец переопределяет канал
    # Сохраняем привязку: chat->channel и owner
    Storage.save_binding(chat_id, channel, user_id)
    # Инициализируем пустые настройки и доверенность
    Storage.save_settings(chat_id, {})
    await update.message.reply_text(
        f'Канал {channel} привязан владельцем @{update.effective_user.username}.'
        'Теперь владелец может выдавать доверенность командой /grant'
    )

# /grant @username - доверенность администрирования другим пользователям чата
async def grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    owner = Storage.get_owner(chat_id)
    if not owner:
        return await update.message.reply_text('Сначала привяжите канал через /link')
    if owner != user_id:
        return await update.message.reply_text('Только владелец канала может выдавать доверенность.')
    if len(context.args) != 1:
        return await update.message.reply_text('Использование: /grant @username')
    username = context.args[0].lstrip('@')
    Storage.grant_trust(chat_id, username)
    await update.message.reply_text(f'@{username} получил доступ к управлению.')

# Регистрация обработчиков
def link_handler(app):
    app.add_handler(CommandHandler('link', link))
    app.add_handler(CommandHandler('grant', grant))
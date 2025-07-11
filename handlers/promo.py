# handlers/promo.py
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from storage.storage import Storage

async def promo_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Работаем только в групповом чате
    if update.effective_chat.type == 'private':
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    # Проверяем привязку
    channel = Storage.get_binding(chat_id)
    if not channel:
        return await update.message.reply_text('Сначала привяжите канал через /link')

    # Проверяем доверенность: владелец или доверенный
    owner = Storage.get_owner(chat_id)
    if user.id != owner and not Storage.is_trusted(chat_id, user.username):
        return await update.message.reply_text('У вас нет прав использовать /promo')

    # Если промо ещё не активировано для этого чата и нет args
    if not context.chat_data.get('promo_accepted') and not context.args:
        return await update.message.reply_text('Введите промокод: /promo CODE')

    # Если указан код аргументом
    if context.args:
        code = context.args[0]
        if Storage.check_promo(code):
            # Устанавливаем флаг, что промо активирован для чата
            context.chat_data['promo_accepted'] = True
            context.user_data['setup_step'] = 'template'
            return await update.message.reply_text(
                'Промокод принят! Пришлите шаблон оформления с полями {tags}, {author}, {communication}, {hiddenlink1}, {hiddenlink2}.'
            )
        else:
            return await update.message.reply_text('Неверный или просроченный промокод.')

    # Если промо уже активировано, переходим к setup
    if context.chat_data.get('promo_accepted'):
        context.user_data['setup_step'] = 'template'
        return await update.message.reply_text(
            'Промокод уже активирован, отправьте шаблон оформления.'
        )

# Создание промокода владельцем бота
async def create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Только владелец (username Treyg0lniik)
    if update.effective_chat.type != 'private':
        return
    if update.effective_user.username != 'Treyg0lniik':
        return
    if len(context.args) != 2:
        return await update.message.reply_text('Использование: /createcode CODE срок_в_днях')
    code, days = context.args
    Storage.add_promo(code, int(days))
    await update.message.reply_text(f'Промокод {code} создан на {days} дней.')

# Регистрация обработчиков

def promo_handler(app):
    app.add_handler(CommandHandler('promo', promo_chat))
    app.add_handler(CommandHandler('createcode', create_code))

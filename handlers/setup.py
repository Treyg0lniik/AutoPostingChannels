# handlers/setup.py
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from handlers.mainmenu import show_menu
from storage.storage import Storage


async def handle_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    step = context.user_data.get('setup_step')

    if update.effective_user is None:
        return  # пришло из канала — ничего не делаем
    
    if step == 'template':
        text = update.message.text
        if '{tags}' in text and '{author}' in text and '{communication}' in text:
            settings = Storage.get_settings(chat_id)
            settings['template'] = text
            Storage.save_settings(chat_id, settings)
            context.user_data['setup_step'] = 'slots'
            await update.message.reply_text('Шаблон сохранён! Введите слоты через пробел (00:00 01:30)')
        else:
            await update.message.reply_text('Ошибка: шаблон должен содержать {tags}, {author} и {communication}.')
    elif step == 'slots':
        raw_slots = update.message.text.split()
        valid = []
        for slot in raw_slots:
            if slot.count(':') != 1:
                continue
            hh, mm = slot.split(':')
            if not (hh.isdigit() and mm.isdigit()):
                continue
            hh, mm = int(hh), int(mm)
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                valid.append(f"{hh:02}:{mm:02}")
        if not valid:
            await update.message.reply_text('Неверный формат. Используйте 00:00 01:30')
            return
        settings = Storage.get_settings(chat_id)
        settings['slots'] = valid
        Storage.save_settings(chat_id, settings)
        context.user_data['setup_step'] = 'communication'
        await update.message.reply_text('Слоты сохранены! Введите текст для {communication}.')
    elif step == 'communication':
        comm = update.message.text
        settings = Storage.get_settings(chat_id)
        settings['communication_text'] = comm
        Storage.save_settings(chat_id, settings)
        context.user_data.pop('setup_step', None)
        await update.message.reply_text('Настройка завершена!')
        await show_menu(update, context)

# Регистрация

def setup_handler(app):
    handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL,
        handle_setup
    )
    app.add_handler(handler)
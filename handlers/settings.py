# handlers/settings.py
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes
from storage.storage import Storage

async def set_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Проверка привязки и промокода
    if not Storage.get_binding(chat_id):
        return await update.message.reply_text("Привяжите канал через /link")
    if not context.chat_data.get('promo_accepted'):
        return await update.message.reply_text("Сначала активируйте промокод: /promo <CODE>")

    # Берём весь текст после команды, включая переносы и HTML
    text = update.message.text.partition(' ')[2]
    if not text:
        return await update.message.reply_text(
            "Использование: /set_template <шаблон>, содержащий {tags}, {author}, {communication}, {hiddenlink1}, {hiddenlink2}."
        )
    # Проверка обязательных полей
    required = ['{tags}', '{author}', '{communication}', '{hiddenlink1}', '{hiddenlink2}']
    missing = [ph for ph in required if ph not in text]
    if missing:
        return await update.message.reply_text(
            f"Шаблон должен содержать следующие поля: {', '.join(required)}. Отсутствуют: {', '.join(missing)}"
        )
    # Сохраняем шаблон
    settings = Storage.get_settings(chat_id)
    settings['template'] = text
    Storage.save_settings(chat_id, settings)
    await update.message.reply_text("✅ Шаблон сохранён.", parse_mode=ParseMode.HTML)

async def set_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not Storage.get_binding(chat_id):
        return await update.message.reply_text("Привяжите канал через /link")
    if not context.chat_data.get('promo_accepted'):
        return await update.message.reply_text("Сначала активируйте промокод: /promo <CODE>")

    valid = []
    for slot in context.args:
        if ':' in slot:
            hh, mm = slot.split(':', 1)
            if hh.isdigit() and mm.isdigit():
                hh_i, mm_i = int(hh), int(mm)
                if 0 <= hh_i < 24 and 0 <= mm_i < 60:
                    valid.append(f"{hh_i:02}:{mm_i:02}")
    if not valid:
        return await update.message.reply_text("Нет валидных слотов. Формат: /set_slots 00:00 13:45")
    settings = Storage.get_settings(chat_id)
    settings['slots'] = valid
    Storage.save_settings(chat_id, settings)
    await update.message.reply_text(f"✅ Слоты сохранены: {', '.join(valid)}")

async def set_comm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not Storage.get_binding(chat_id):
        return await update.message.reply_text("Привяжите канал через /link")
    if not context.chat_data.get('promo_accepted'):
        return await update.message.reply_text("Сначала активируйте промокод: /promo <CODE>")

    text = update.message.text.partition(' ')[2]
    if not text:
        return await update.message.reply_text("Использование: /set_comm <текст>")
    settings = Storage.get_settings(chat_id)
    settings['communication_text'] = text
    Storage.save_settings(chat_id, settings)
    await update.message.reply_text("✅ Communication сохранён.")

async def set_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not Storage.get_binding(chat_id):
        return await update.message.reply_text("Привяжите канал через /link")
    if not context.chat_data.get('promo_accepted'):
        return await update.message.reply_text("Сначала активируйте промокод: /promo <CODE>")

    parts = update.message.text.partition(' ')[2].split(maxsplit=3)
    if len(parts) != 4:
        return await update.message.reply_text(
            "Использование: /set_links <текст1> <ссылка1> <текст2> <ссылка2>"
        )
    lt1, url1, lt2, url2 = parts
    settings = Storage.get_settings(chat_id)
    settings['hiddenlink1_text'] = lt1
    settings['hiddenlink1_url'] = url1
    settings['hiddenlink2_text'] = lt2
    settings['hiddenlink2_url'] = url2
    Storage.save_settings(chat_id, settings)
    await update.message.reply_text("✅ Скрытые ссылки сохранены.")

async def set_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /set_whitelist #art #edit #3D #meme …
    Сохраняет список разрешённых хэштегов (без учёта регистра).
    """
    chat_id = update.effective_chat.id
    if not Storage.get_binding(chat_id):
        return await update.message.reply_text("Привяжите канал через /link")
    # args — список строк вида "#tag"
    raw = context.args
    if not raw:
        return await update.message.reply_text(
            "Использование:\n"
            "/set_whitelist #art #edit #3D #meme #animation #cosplay #ai"
        )
    # Нормализуем: убираем ведущий '#', в нижний регистр
    wl = [tag.lstrip('#').lower() for tag in raw if tag.strip()]
    settings = Storage.get_settings(chat_id)
    settings['whitelist'] = wl
    Storage.save_settings(chat_id, settings)
    await update.message.reply_text(
        f"✅ Белый список хэштегов сохранён: {', '.join('#'+t for t in wl)}",
        parse_mode=ParseMode.HTML
    )
# Регистрация хендлеров

def register_settings(app):
    app.add_handler(CommandHandler('set_whitelist', set_whitelist))
    app.add_handler(CommandHandler('set_template', set_template))
    app.add_handler(CommandHandler('set_slots', set_slots))
    app.add_handler(CommandHandler('set_comm', set_comm))
    app.add_handler(CommandHandler('set_links', set_links))

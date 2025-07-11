# handlers/testpost.py
import asyncio
import datetime
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from storage.storage import Storage

async def send_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    channel = Storage.get_binding(chat_id)
    if not channel:
        return await update.message.reply_text("Привяжите канал через /link")

    settings = Storage.get_settings(chat_id)
    slots = settings.get('slots', [])
    template = settings.get('template')
    comm = settings.get('communication_text', '')
    if not slots or not template:
        return await update.message.reply_text(
            "Сначала задайте шаблон и слоты:\n"
            "/set_template …\n"
            "/set_slots …"
        )

    # 1) Определяем, откуда берём фото и args
    if update.message.photo and update.message.caption and update.message.caption.startswith('/send_test'):
        # Сценарий: фото + подпись-команда
        photo_msg = update.message
        args_text = update.message.caption[len('/send_test'):].strip()
        parts = args_text.split()
    elif update.message.reply_to_message and update.message.reply_to_message.photo:
        # Сценарий: reply на фото
        photo_msg = update.message.reply_to_message
        parts = context.args
    else:
        return await update.message.reply_text(
            "Ответьте на фото командой:\n"
            "/send_test tag1 tag2 author_name\n"
            "или отправьте фото с подписью-командой."
        )

    # 2) Парсим теги и автора
    if len(parts) < 3:
        return await update.message.reply_text(
            "Нужно минимум два тега и автор, например:\n"
            "/send_test tag1 tag2 author_name"
        )
    tags_list = parts[:-1]
    tags = ' '.join(f"#{t.lstrip('#')}" for t in tags_list)
    author = parts[-1]

    # 3) Ищем следующий незанятый слот до 365 дней
    now = datetime.datetime.utcnow()
    scheduled_ts = Storage.get_scheduled(chat_id)
    next_dt = None
    for day_offset in range(365):
        date = now + datetime.timedelta(days=day_offset)
        for slot in sorted(slots):
            hh, mm = map(int, slot.split(':'))
            candidate = date.replace(hour=hh, minute=mm, second=0, microsecond=0)
            ts = int(candidate.timestamp())
            if ts > int(now.timestamp()) and ts not in scheduled_ts:
                next_dt = candidate
                break
        if next_dt:
            break
    if not next_dt:
        return await update.message.reply_text("Не найден свободный слот для постинга.")

    # 4) Формируем текст по шаблону
    post_text = (
        template
        .replace('{tags}', tags)
        .replace('{author}', author)
        .replace('{communication}', comm)
    )

    # 5) Записываем расписание и планируем
    ts = int(next_dt.timestamp())
    Storage.add_scheduled(chat_id, ts)

    file_id = photo_msg.photo[-1].file_id
    delay = (next_dt - now).total_seconds()

    async def _execute():
        await asyncio.sleep(delay)
        await context.bot.send_photo(chat_id=channel, photo=file_id, caption=post_text)
        Storage.remove_scheduled(chat_id, ts)

    context.application.create_task(_execute())

    await update.message.reply_text(
        f"✅ Пост запланирован на {next_dt.strftime('%Y-%m-%d %H:%M')} UTC"
    )

async def slots_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    timestamps = Storage.get_scheduled(chat_id)
    if not timestamps:
        return await update.message.reply_text("Нет запланированных постов.")
    now_ts = int(datetime.datetime.utcnow().timestamp())
    # Минуты до каждой будущей отправки
    diffs = [str((ts - now_ts) // 60) for ts in sorted(timestamps) if ts > now_ts]
    if not diffs:
        return await update.message.reply_text("Нет будущих запланированных постов.")
    text = ", ".join(diffs)
    await update.message.reply_text(
        f"Минут до отправки запланированных постов: {text}"
    )

def register_testpost(app):
    app.add_handler(CommandHandler('send_test', send_test))
    app.add_handler(CommandHandler('slots_status', slots_status))

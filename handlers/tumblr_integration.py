# handlers/tumblr_integration.py
import os
import datetime
import asyncio
import httpx
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from storage.storage import Storage

SEARCH_URL = "https://api.tumblr.com/v2/tagged"
TUMBLR_API_KEY  = os.getenv("TUMBLR_API_KEY")

def extract_img(body: str) -> str | None:
    soup = BeautifulSoup(body, "html.parser")
    img = soup.find("img")
    return img["src"] if img and img.get("src") else None

async def search_tumblr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    channel = Storage.get_binding(chat_id)
    if not channel:
        return await update.message.reply_text("Сначала привяжите канал через /link")
    owner = Storage.get_owner(chat_id)
    if user.id != owner and not Storage.is_trusted(chat_id, user.username):
        return await update.message.reply_text("Нет прав на поиск Tumblr-постов")

    query = " ".join(context.args).strip()
    if not query:
        return await update.message.reply_text("Использование: /tumblr <запрос>")

    async with httpx.AsyncClient() as client:
        resp = await client.get(SEARCH_URL, params={"tag": query, "api_key": TUMBLR_API_KEY, "limit": 50}, timeout=10)
    posts = resp.json().get("response", [])

    results = []
    for item in posts:
        url = None
        if item.get("type") == "photo":
            photos = item.get("photos", [])
            if photos:
                url = photos[0]["original_size"]["url"]
        elif item.get("type") == "text":
            url = extract_img(item.get("body", ""))
        if not url:
            continue
        author = item.get("blog_name", "unknown")
            # убираем пробелы внутри каждого тега
        raw_tags = [t.replace(" ", "") for t in item.get("tags", [])]
        # строим собственно строку для превью
        tags = " ".join(f"#{t}" for t in raw_tags)
        results.append({
        "url": url,
        "author": author,
        "raw_tags": raw_tags,   # сохраним массив
        "tags": tags            # на случай fallback
        })


    if not results:
        return await update.message.reply_text(f"По запросу «{query}» не найдено изображений.")

# Сохраняем результаты и состояние для динамической подгрузки
    context.chat_data["tumblr_posts"] = results
    context.chat_data["tumblr_index"] = 0
    context.chat_data["tumblr_query"] = query
    context.chat_data["tumblr_offset"] = len(results)
    await show_tumblr(update, context)

async def show_tumblr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    i = context.chat_data["tumblr_index"]
    posts = context.chat_data["tumblr_posts"]
    item = context.chat_data["tumblr_posts"][i]
    chat_id = update.effective_chat.id

    settings = Storage.get_settings(chat_id)

    # 1) фильтруем теги по whitelist
        # --- собираем теги из raw_tags, очищаем пробелы и фильтруем по whitelist ---
    all_tags = item.get("raw_tags", [])              # ['murderdrones','serialdesignationv',...]
    wl = settings.get('whitelist', [])               # ['art','edit',...]
    if wl:
        # оставляем только те, что есть в wl (без учета регистра)
        filtered = [f"#{t}" for t in all_tags if t.lower() in wl]
        tags_str = " ".join(filtered)
    else:
        # если whitelist не задан — показываем все, уже без пробелов
        tags_str = " ".join(f"#{t}" for t in all_tags)


    # 2) готовим остальные поля и caption
    template = settings.get("template", "{tags}\n{author}\n{communication}\n{hiddenlink1}\n{hiddenlink2}")
    comm = settings.get("communication_text", "")
    # скрытые ссылки, как было
    hl1 = settings.get("hiddenlink1_text", "")
    hu1 = settings.get("hiddenlink1_url", "")
    hl2 = settings.get("hiddenlink2_text", "")
    hu2 = settings.get("hiddenlink2_url", "")
    h1 = f'<a href="{hu1}">{hl1}</a>' if hl1 and hu1 else ''
    h2 = f'<a href="{hu2}">{hl2}</a>' if hl2 and hu2 else ''

    caption = (
        template
        .replace("{tags}", tags_str)
        .replace("{author}", f"@{item['author']}")
        .replace("{communication}", comm)
        .replace("{hiddenlink1}", h1)
        .replace("{hiddenlink2}", h2)
    )

    kb = []
    if i > 0:
        kb.append(InlineKeyboardButton("◀ Назад", callback_data="nav|prev"))
    kb.append(InlineKeyboardButton("✅ Запланировать", callback_data="nav|schedule"))
    if i < len(posts) - 1:
        kb.append(InlineKeyboardButton("▶ Вперёд", callback_data="nav|next"))
    kb.append(InlineKeyboardButton("❌ Завершить", callback_data="nav|end"))
    markup = InlineKeyboardMarkup([kb])

    if update.callback_query:
        await update.callback_query.answer()
        media = InputMediaPhoto(media=item["url"], caption=caption)
        await update.callback_query.edit_message_media(media=media, reply_markup=markup)
    else:
        await update.message.reply_photo(photo=item["url"], caption=caption, reply_markup=markup)

async def tumblr_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split("|")[1]

    if action == 'prev':
        context.chat_data['tumblr_index'] = max(context.chat_data['tumblr_index'] - 1, 0)
        return await show_tumblr(update, context)
    if action == 'next':
        idx = context.chat_data['tumblr_index']
        posts = context.chat_data['tumblr_posts']

        # Проверяем, дошли ли до конца списка
        if idx == len(posts) - 1:
            tag = context.chat_data.get('tumblr_query')
            offset = context.chat_data.get('tumblr_offset', len(posts))

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    SEARCH_URL,
                    params={"tag": tag, "api_key": TUMBLR_API_KEY, "limit": 50, "offset": offset},
                    timeout=10
                )

            new_items = []
            for item in resp.json().get("response", []):
                url = None
                if item.get("type") == "photo":
                    photos = item.get("photos", [])
                    if photos:
                        url = photos[0]["original_size"]["url"]
                elif item.get("type") == "text":
                    url = extract_img(item.get("body", ""))
                if not url:
                    continue
                author = item.get("blog_name", "unknown")
                tags = " ".join(f"#{t}" for t in item.get("tags", []))
                new_items.append({"url": url, "author": author, "tags": tags})

            if new_items:
                posts.extend(new_items)
                context.chat_data["tumblr_offset"] = offset + len(new_items)
            else:
                return await update.callback_query.answer("Больше постов не найдено.", show_alert=True)

        context.chat_data['tumblr_index'] = min(idx + 1, len(context.chat_data['tumblr_posts']) - 1)
        return await show_tumblr(update, context)

    if action == 'schedule':
        return await schedule_current(update, context)

    if action == 'end':
        context.chat_data.pop('tumblr_posts', None)
        context.chat_data.pop('tumblr_index', None)
        context.chat_data.pop('tumblr_query', None)
        context.chat_data.pop('tumblr_offset', None)
        return await query.edit_message_caption(caption='Сессия завершена.')

async def schedule_current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # просто закрываем «часики»

    chat_id = update.effective_chat.id
    # Проверяем, что сессия активна
    if "tumblr_posts" not in context.chat_data:
        return await query.message.reply_text("Нет активной сессии.")

    # Текущий пост
    idx = context.chat_data["tumblr_index"]
    item = context.chat_data["tumblr_posts"][idx]

    # Настройки и слоты
    settings = Storage.get_settings(chat_id)
    slots = settings.get("slots", [])
    if not slots:
        return await query.message.reply_text("Сначала задайте слоты: /set_slots")

    # Ищем ближайший свободный слот
    now = datetime.datetime.utcnow()
    used = Storage.get_scheduled(chat_id)
    next_dt = None
    for day_offset in range(365):
        day = now + datetime.timedelta(days=day_offset)
        for slot in sorted(slots):
            hh, mm = map(int, slot.split(":"))
            cand = day.replace(hour=hh, minute=mm, second=0, microsecond=0)
            ts = int(cand.timestamp())
            if ts > int(now.timestamp()) and ts not in used:
                next_dt = cand
                break
        if next_dt:
            break
    if not next_dt:
        return await query.message.reply_text("Нет доступных слотов для планирования.")

    # Формируем caption точно так же, как в show_tumblr()
    template = settings["template"]
    comm = settings.get("communication_text", "")
    hl1_t = settings.get("hiddenlink1_text", "")
    hl1_u = settings.get("hiddenlink1_url", "")
    hl2_t = settings.get("hiddenlink2_text", "")
    hl2_u = settings.get("hiddenlink2_url", "")
    hl1_html = f'<a href="{hl1_u}">{hl1_t}</a>' if hl1_t and hl1_u else ""
    hl2_html = f'<a href="{hl2_u}">{hl2_t}</a>' if hl2_t and hl2_u else ""
    caption = (
        template
        .replace("{tags}", item["tags"])
        .replace("{author}", f"@{item['author']}")
        .replace("{communication}", comm)
        .replace("{hiddenlink1}", hl1_html)
        .replace("{hiddenlink2}", hl2_html)
    )

    # Сохраняем слот и планируем отправку в канал
    ts = int(next_dt.timestamp())
    Storage.add_scheduled(chat_id, ts)
    delay = (next_dt - now).total_seconds()
    channel_id = Storage.get_binding(chat_id)

    async def _job():
        await asyncio.sleep(delay)
        await context.bot.send_photo(
            chat_id=channel_id,
            photo=item["url"],
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        Storage.remove_scheduled(chat_id, ts)

    context.application.create_task(_job())

    # Подтверждаем пользователю
    await query.message.reply_text(
        f"✅ Пост запланирован на {next_dt.strftime('%Y-%m-%d %H:%M')} UTC "
        f"и будет отправлен в канал @{channel_id}",
        parse_mode=ParseMode.HTML
    )

# Регистрация

def register_tumblr(app):
    app.add_handler(CommandHandler('tumblr', search_tumblr))
    app.add_handler(CallbackQueryHandler(tumblr_nav, pattern=r'^nav\|'))
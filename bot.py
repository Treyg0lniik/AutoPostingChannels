# bot.py
import os
import asyncio
import logging
from threading import Thread

from aiohttp import web
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Вместо config.py читаем токены из окружения
BOT_TOKEN       = os.getenv("BOT_TOKEN")
TUMBLR_API_KEY  = os.getenv("TUMBLR_API_KEY")

# Если не заданы — аварийно завершаем
if not BOT_TOKEN:
    raise RuntimeError("Не задана переменная окружения BOT_TOKEN")
if not TUMBLR_API_KEY:
    raise RuntimeError("Не задана переменная окружения TUMBLR_API_KEY")

# Подключаем все ваши хэндлеры
from handlers.link               import link_handler
from handlers.promo              import promo_handler
from handlers.setup              import setup_handler
from handlers.settings           import register_settings
from handlers.testpost           import register_testpost
from handlers.tumblr_integration import register_tumblr
from handlers.backup             import register_backup

# ——— Health‑endpoint на aiohttp ——————————————
async def health(request):
    return web.Response(text="OK")

async def run_health_server():
    app = web.Application()
    app.add_routes([web.get("/", health)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

def start_health_server():
    """Запускаем aiohttp в отдельном потоке."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_health_server())
    loop.run_forever()

# ——— Основная функция бота —————————————————————
def main():
    logging.basicConfig(level=logging.INFO)

    # 1) Старт health‑сервера в фоне
    Thread(target=start_health_server, daemon=True).start()

    # 2) Старт Telegram‑бота
    app = Application.builder().token(BOT_TOKEN).build()
    # прокидываем API‑ключ TumblR в bot_data, чтобы хэндлер мог его взять
    app.bot_data["TUMBLR_API_KEY"] = TUMBLR_API_KEY

    # Регистрация ваших хэндлеров
    link_handler(app)
    promo_handler(app)
    setup_handler(app)
    register_settings(app)
    register_testpost(app)
    register_tumblr(app)
    register_backup(app)

    # Запуск долгого опроса
    app.run_polling()

if __name__ == "__main__":
    main()

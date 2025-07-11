from telegram.ext import CallbackQueryHandler
from handlers.promo import callback_promo


def admin_handler(app):
    app.add_handler(CallbackQueryHandler(callback_promo))
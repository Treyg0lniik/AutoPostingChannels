from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes
from storage.storage import Storage

MENU_CALLBACK = 'menu_edit'
EDIT_TEMPLATE = 'edit_template'
EDIT_SLOTS = 'edit_slots'
EDIT_COMM = 'edit_comm'


def mainmenu_handler(app):
    app.add_handler(CommandHandler('menu', show_menu))
    app.add_handler(CallbackQueryHandler(menu_callback_handler, pattern=f'^{MENU_CALLBACK}'))

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = Storage.get_settings(user_id)
    template = settings.get('template', '—')
    slots = settings.get('slots', [])
    comm = settings.get('communication_text', '—')

    keyboard = [
        [InlineKeyboardButton(f"Шаблон: {template[:10]}...", callback_data=f"{MENU_CALLBACK}|{EDIT_TEMPLATE}")],
        [InlineKeyboardButton(f"Слоты: {', '.join(slots)}", callback_data=f"{MENU_CALLBACK}|{EDIT_SLOTS}")],
        [InlineKeyboardButton(f"Communication: {comm[:10]}...", callback_data=f"{MENU_CALLBACK}|{EDIT_COMM}")],
    ]
    await update.message.reply_text('Главное меню:', reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, action = query.data.split('|', 1)
    if action == EDIT_TEMPLATE:
        context.user_data['setup_step'] = 'template'
        await query.edit_message_text('Отправьте новый шаблон с {tags}, {author}, {communication}.')
    elif action == EDIT_SLOTS:
        context.user_data['setup_step'] = 'slots'
        await query.edit_message_text('Введите новые слоты (HH:MM через пробел).')
    elif action == EDIT_COMM:
        context.user_data['setup_step'] = 'communication'
        await query.edit_message_text('Введите новый текст для {communication}.')
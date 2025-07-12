import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from src.telegram_food_boot.database import get_db_connection
import httpx
from src.telegram_food_boot.utils import load_food_data, translations
from src.telegram_food_boot.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT

# Conversation states
SIGNUP_USERNAME, SIGNUP_PASSWORD = range(2)
LOGIN_USERNAME, LOGIN_PASSWORD = range(2)

logger = logging.getLogger(__name__)


async def check_user_authenticated(user_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        return user is not None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_authenticated = await check_user_authenticated(user_id)

    keyboard = [
        [InlineKeyboardButton("Cadastrar", callback_data="signup")],
        [InlineKeyboardButton("Login", callback_data="login")],
        [InlineKeyboardButton("Usar sem login", callback_data="anonymous")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_authenticated:
        welcome_text = (
            "Bem-vindo ao NutriBot, {}! 😊\n"
            "Use os comandos no menu para rastrear refeições, água, metas e mais.\n"
            "Ex.: /meals, /goals, /water, /summary, /calculations, /reminders, /tips, /foods"
        ).format(update.effective_user.first_name)
    else:
        welcome_text = (
            "Bem-vindo ao NutriBot! 😊\n"
            "Faça login ou cadastre-se para acessar todas as funcionalidades.\n"
            "Você também pode usar sem login para ver dicas ou a tabela de alimentos com /foods."
        )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "signup":
        await query.message.reply_text("Por favor, envie seu nome de usuário.")
        return SIGNUP_USERNAME
    elif query.data == "login":
        await query.message.reply_text("Por favor, envie seu nome de usuário.")
        return LOGIN_USERNAME
    elif query.data == "anonymous":
        await query.message.reply_text("Modo anônimo ativado. Use /tips ou /foods.")
        return ConversationHandler.END
    return ConversationHandler.END


async def signup_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["signup_username"] = update.message.text
    await update.message.reply_text("Agora, envie sua senha.")
    return SIGNUP_PASSWORD


async def signup_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text
    username = context.user_data.get("signup_username")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                # Adjust to match API base URL
                f"{WEBHOOK_URL.replace('webhook', '')}api/v1/users",
                json={"username": username, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            user_id = update.effective_user.id
            access_token = data.get("access_token")
            if access_token:
                context.user_data["access_token"] = access_token
                async with get_db_connection() as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                        (user_id, username)
                    )
                    await db.commit()
                await update.message.reply_text("Cadastro realizado com sucesso! Use /start para continuar.")
            else:
                await update.message.reply_text("Erro ao cadastrar. Tente novamente.")
        except httpx.HTTPError as e:
            logger.error(f"API error during signup: {e}")
            await update.message.reply_text("Erro ao conectar com a API. Tente novamente.")
        except Exception as e:
            logger.error(f"Unexpected error during signup: {e}")
            await update.message.reply_text("Erro inesperado. Tente novamente.")

    return ConversationHandler.END


async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["login_username"] = update.message.text
    await update.message.reply_text("Agora, envie sua senha.")
    return LOGIN_PASSWORD


async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text
    username = context.user_data.get("login_username")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{WEBHOOK_URL.replace('webhook', '')}api/v1/login",
                data={"username": username, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            user_id = update.effective_user.id
            access_token = data.get("access_token")
            if access_token:
                context.user_data["access_token"] = access_token
                async with get_db_connection() as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                        (user_id, username)
                    )
                    await db.commit()
                await update.message.reply_text("Login realizado com sucesso! Use /start para continuar.")
            else:
                await update.message.reply_text("Usuário ou senha incorretos. Tente novamente.")
        except httpx.HTTPError as e:
            logger.error(f"API error during login: {e}")
            await update.message.reply_text("Erro ao conectar com a API. Tente novamente.")
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            await update.message.reply_text("Erro inesperado. Tente novamente.")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END


async def meal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    await update.message.reply_text("Registre sua refeição: /meals breakfast 1 100")


async def goal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    await update.message.reply_text("Defina sua meta: /goals energy_kcal 2000")


async def water_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    await update.message.reply_text("Registre água consumida: /water 2000")


async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{WEBHOOK_URL.replace('webhook', '')}api/v1/summary/{update.effective_user.id}",
                headers={
                    "Authorization": f"Bearer {context.user_data.get('access_token')}"}
            )
            response.raise_for_status()
            summary = response.json()
            await update.message.reply_text(summary.get('text', 'Erro ao obter resumo.'), parse_mode='Markdown')
        except httpx.HTTPError as e:
            logger.error(f"API error during summary: {e}")
            await update.message.reply_text("Erro ao conectar com a API.")


async def calc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    await update.message.reply_text("Realize um cálculo: /calculations imc 70 175")


async def reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    await update.message.reply_text("Configure um lembrete: /reminders meal_reminder 12:00")


async def tips_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{WEBHOOK_URL.replace('webhook', '')}api/v1/tips")
            response.raise_for_status()
            tip = response.json().get("tip")
            await update.message.reply_text(f"Dica do dia: {tip}")
        except httpx.HTTPError as e:
            logger.error(f"API error during tips: {e}")
            await update.message.reply_text("Erro ao conectar com a API.")


async def foods_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    food_data = load_food_data()
    if not food_data:
        await update.message.reply_text(translations['pt']['no_foods_found'])
        return

    message = "📋 *Tabela de Alimentos*\n\n"
    for food in food_data[:10]:
        message += (
            f"ID: {food['id']}\n"
            f"Alimento: {food['description']}\n"
            f"Calorias: {food['energy_kcal']} kcal/100g\n"
            f"Proteínas: {food['protein_g']}g/100g\n"
            f"Carboidratos: {food['carbohydrate_g']}g/100g\n"
            f"Lipídios: {food['lipid_g']}g/100g\n"
            f"Fibras: {food['fiber_g']}g/100g\n\n"
        )
    message += "Use /foods para ver mais ou /meals para registrar uma refeição."
    await update.message.reply_text(message, parse_mode='Markdown')


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    application = Application.builder().token(BOT_TOKEN).build()

    # Signup conversation handler
    signup_conv = ConversationHandler(
        # Start with button handler
        entry_points=[CommandHandler("signup", button_handler)],
        states={
            SIGNUP_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup_username)],
            SIGNUP_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # Login conversation handler
    login_conv = ConversationHandler(
        # Start with button handler
        entry_points=[CommandHandler("login", button_handler)],
        states={
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(signup_conv)
    application.add_handler(login_conv)
    application.add_handler(CommandHandler("meals", meal_handler))
    application.add_handler(CommandHandler("goals", goal_handler))
    application.add_handler(CommandHandler("water", water_handler))
    application.add_handler(CommandHandler("summary", summary_handler))
    application.add_handler(CommandHandler("calculations", calc_handler))
    application.add_handler(CommandHandler("reminders", reminder_handler))
    application.add_handler(CommandHandler("tips", tips_handler))
    application.add_handler(CommandHandler("foods", foods_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    # Start bot with webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=WEBHOOK_PORT,
        url_path="/webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook",
    )


if __name__ == "__main__":
    main()

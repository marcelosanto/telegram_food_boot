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
from src.telegram_food_boot.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT, API_BASE_URL

# Conversation states
SIGNUP_USERNAME, SIGNUP_PASSWORD = range(2)
LOGIN_USERNAME, LOGIN_PASSWORD = range(2, 4)
MEAL_TYPE, MEAL_FOOD, MEAL_QUANTITY = range(4, 7)

logger = logging.getLogger(__name__)


async def check_user_authenticated(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        async with get_db_connection() as db:
            logger.info(f"Checking authentication for user_id: {user_id}")
            cursor = await db.execute(
                "SELECT user_id, username FROM users WHERE user_id = ?", (
                    user_id,)
            )
            user = await cursor.fetchone()
            if user:
                cursor = await db.execute(
                    "SELECT access_token FROM user_tokens WHERE user_id = ?", (
                        user_id,)
                )
                token = await cursor.fetchone()
                if token and token[0]:
                    context.user_data["access_token"] = token[0]
                    return True
            return False
    except Exception as e:
        logger.error(f"Database error in check_user_authenticated: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_authenticated = await check_user_authenticated(user_id, context)

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
    if query:
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


async def signup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Por favor, envie seu nome de usuário.")
    return SIGNUP_USERNAME


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Por favor, envie seu nome de usuário.")
    return LOGIN_USERNAME


async def signup_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["signup_username"] = update.message.text
    await update.message.reply_text("Agora, envie sua senha.")
    return SIGNUP_PASSWORD


async def signup_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text
    username = context.user_data.get("signup_username")
    user_id = update.effective_user.id

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/users",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                context.user_data["access_token"] = access_token
                async with get_db_connection() as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                        (user_id, username)
                    )
                    await db.execute(
                        "INSERT OR REPLACE INTO user_tokens (user_id, access_token) VALUES (?, ?)",
                        (user_id, access_token)
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
    user_id = update.effective_user.id

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                logger.info(
                    f"Received access_token: {access_token} for user_id: {user_id}")
                context.user_data["access_token"] = access_token
                async with get_db_connection() as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                        (user_id, username)
                    )
                    await db.execute(
                        "INSERT OR REPLACE INTO user_tokens (user_id, access_token) VALUES (?, ?)",
                        (user_id, access_token)
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


async def meal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(
        f"Received command: /meals for user {update.effective_user.id}")
    if not await check_user_authenticated(update.effective_user.id, context):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return ConversationHandler.END
    context.user_data["meals"] = {}
    keyboard = [
        [InlineKeyboardButton("Café da manhã", callback_data="breakfast")],
        [InlineKeyboardButton("Almoço", callback_data="lunch")],
        [InlineKeyboardButton("Jantar", callback_data="dinner")],
        [InlineKeyboardButton("Lanche", callback_data="snack")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecione o tipo de refeição:", reply_markup=reply_markup)
    return MEAL_TYPE


async def meal_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data["meals"]["meal_type"] = query.data
        food_data = load_food_data()
        keyboard = [[InlineKeyboardButton(
            food["description"], callback_data=f"food_{food['id']}")] for food in food_data[:5]]
        keyboard.append([InlineKeyboardButton(
            "Mais opções", callback_data="more_foods")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Selecione um alimento:", reply_markup=reply_markup)
        return MEAL_FOOD
    return MEAL_TYPE


async def meal_food_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == "more_foods":
            food_data = load_food_data()
            keyboard = [[InlineKeyboardButton(
                food["description"], callback_data=f"food_{food['id']}")] for food in food_data[5:10]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Mais opções de alimentos:", reply_markup=reply_markup)
            return MEAL_FOOD
        context.user_data["meals"]["food_id"] = int(
            query.data.replace("food_", ""))
        await query.message.reply_text("Digite a quantidade (em gramas):")
        return MEAL_QUANTITY
    return MEAL_FOOD


async def meal_quantity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    quantity = update.message.text
    if not quantity.isdigit():
        await update.message.reply_text("Por favor, insira um número válido para a quantidade.")
        return MEAL_QUANTITY
    context.user_data["meals"]["quantity"] = int(quantity)
    token = context.user_data.get("access_token")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/meals",
                json=context.user_data["meals"],
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            await update.message.reply_text("Refeição registrada com sucesso!")
        except httpx.HTTPError as e:
            logger.error(f"API error during meal: {e}")
            await update.message.reply_text("Erro ao registrar refeição. Tente novamente.")
    return ConversationHandler.END


async def water_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f"Received command: /water for user {update.effective_user.id}")
    if not await check_user_authenticated(update.effective_user.id, context):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    args = context.args
    if not args or len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Use: /water <quantidade_em_ml>, ex.: /water 500")
        return
    amount = int(args[0])
    token = context.user_data.get("access_token")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/water",
                json={"user_id": update.effective_user.id, "amount": amount},
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            await update.message.reply_text(f"Água ({amount}ml) registrada com sucesso!")
        except httpx.HTTPError as e:
            logger.error(f"API error during water: {e}")
            await update.message.reply_text("Erro ao registrar água. Tente novamente.")


async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f"Received command: /summary for user {update.effective_user.id}")
    if not await check_user_authenticated(update.effective_user.id, context):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    token = context.user_data.get("access_token")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/summary/{update.effective_user.id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            summary = response.json()
            await update.message.reply_text(summary.get('text', 'Erro ao obter resumo.'), parse_mode='Markdown')
        except httpx.HTTPError as e:
            logger.error(f"API error during summary: {e}")
            await update.message.reply_text("Erro ao conectar com a API.")


async def calc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f"Received command: /calculations for user {update.effective_user.id}")
    if not await check_user_authenticated(update.effective_user.id, context):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    args = context.args
    if not args or len(args) < 3 or args[0] not in ["imc", "tmb", "tdee", "fat"]:
        await update.message.reply_text("Use: /calculations <tipo> <peso> <altura> [idade] [sexo] [atividade], ex.: /calculations imc 70 175")
        return
    calc_type = args[0]
    weight = float(args[1])
    height = float(args[2])
    data = {"calc_type": calc_type, "weight": weight, "height": height}
    if len(args) > 3:
        data["age"] = int(args[3])
        data["gender"] = args[4] if len(args) > 4 else None
        if calc_type == "tdee" and len(args) > 5:
            data["activity_level"] = args[5]
    token = context.user_data.get("access_token")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/calculations",
                json=data,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            await update.message.reply_text(response.json()["message"])
        except httpx.HTTPError as e:
            logger.error(f"API error during calculation: {e}")
            await update.message.reply_text("Erro ao realizar cálculo. Tente novamente.")


async def goal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f"Received command: /goals for user {update.effective_user.id}")
    if not await check_user_authenticated(update.effective_user.id, context):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    args = context.args
    if not args or len(args) != 2 or not args[1].isdigit():
        await update.message.reply_text("Use: /goals <nutriente> <valor>, ex.: /goals energy_kcal 2000")
        return
    nutrient = args[0]
    value = int(args[1])
    token = context.user_data.get("access_token")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/goals",
                json={"nutrient": nutrient, "value": value},
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            await update.message.reply_text(response.json()["message"])
        except httpx.HTTPError as e:
            logger.error(f"API error during goal: {e}")
            await update.message.reply_text("Erro ao definir meta. Tente novamente.")


async def reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f"Received command: /reminders for user {update.effective_user.id}")
    if not await check_user_authenticated(update.effective_user.id, context):
        await update.message.reply_text("Você precisa estar logado para usar este comando. Use /login ou /signup.")
        return
    args = context.args
    if not args or len(args) != 2 or not ":" in args[1]:
        await update.message.reply_text("Use: /reminders <tipo> <hora>, ex.: /reminders meal_reminder 12:00")
        return
    reminder_type = args[0]
    time = args[1]
    token = context.user_data.get("access_token")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/reminders",
                json={"type": reminder_type, "time": time},
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            await update.message.reply_text(response.json()["message"])
        except httpx.HTTPError as e:
            logger.error(f"API error during reminder: {e}")
            await update.message.reply_text("Erro ao configurar lembrete. Tente novamente.")


async def tips_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Received command: /tips for user {update.effective_user.id}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/tips",
            )
            response.raise_for_status()
            tip = response.json().get("tip")
            await update.message.reply_text(f"Dica do dia: {tip}")
        except httpx.HTTPError as e:
            logger.error(f"API error during tips: {e}")
            await update.message.reply_text("Erro ao conectar com a API.")


async def foods_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(
        f"Received command: /foods for user {update.effective_user.id}")
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
        entry_points=[CommandHandler("signup", signup_command)],
        states={
            SIGNUP_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup_username)],
            SIGNUP_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, signup_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # Login conversation handler
    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login_command)],
        states={
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # Meal conversation handler
    meal_conv = ConversationHandler(
        entry_points=[CommandHandler("meals", meal_handler)],
        states={
            MEAL_TYPE: [CallbackQueryHandler(meal_type_handler)],
            MEAL_FOOD: [CallbackQueryHandler(meal_food_handler)],
            MEAL_QUANTITY: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, meal_quantity_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(signup_conv)
    application.add_handler(login_conv)
    application.add_handler(meal_conv)
    application.add_handler(CommandHandler("water", water_handler))
    application.add_handler(CommandHandler("summary", summary_handler))
    application.add_handler(CommandHandler("calculations", calc_handler))
    application.add_handler(CommandHandler("goals", goal_handler))
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

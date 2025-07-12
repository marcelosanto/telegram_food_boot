import json
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.telegram_food_boot.database import get_db_connection
from src.telegram_food_boot.utils import load_food_data

API_BASE_URL = "http://localhost:8000/api/v1"

async def check_user_authenticated(user_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        return user is not None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_authenticated = await check_user_authenticated(user_id)
    
    keyboard = [
        [InlineKeyboardButton("Cadastrar", callback_data="signup_username")],
        [InlineKeyboardButton("Login", callback_data="login_username")],
        [InlineKeyboardButton("Usar sem login", callback_data="anonymous")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_authenticated:
        welcome_text = (
            "Bem-vindo ao NutriBot, {}! 😊\n"
            "Use os comandos no menu para rastrear refeições, água, metas e mais.\n"
            "Ex.: /meals, /goals, /water, /summary, /calculations, /reminders, /tips"
        ).format(update.effective_user.first_name)
    else:
        welcome_text = (
            "Bem-vindo ao NutriBot! 😊\n"
            "Faça login ou cadastre-se para acessar todas as funcionalidades.\n"
            "Você também pode usar sem login para ver dicas ou a tabela de alimentos."
        )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Por favor, envie seu nome de usuário.")
    return SIGNUP_USERNAME

async def signup_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Por favor, envie seu nome de usuário.")
    return SIGNUP_USERNAME

async def signup_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["signup_username"] = update.message.text
    await update.message.reply_text("Agora, envie sua senha.")
    return SIGNUP_PASSWORD

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Por favor, envie seu nome de usuário.")
    return LOGIN_USERNAME

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Por favor, envie seu nome de usuário.")
    return LOGIN_USERNAME

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["login_username"] = update.message.text
    await update.message.reply_text("Agora, envie sua senha.")
    return LOGIN_PASSWORD

async def signup_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data.get("signup_username")
    password = update.message.text
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/users",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                user_id = update.effective_user.id
                async with get_db_connection() as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                        (user_id, username)
                    )
                    await db.commit()
                await update.message.reply_text(
                    "Cadastro realizado com sucesso! Use /start para continuar."
                )
            else:
                await update.message.reply_text(
                    "Erro ao cadastrar. Tente outro nome de usuário."
                )
        except httpx.HTTPError:
            await update.message.reply_text("Erro ao conectar com a API.")
    
    return ConversationHandler.END

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data.get("login_username")
    password = update.message.text
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                user_id = update.effective_user.id
                async with get_db_connection() as db:
                    await db.execute(
                        "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                        (user_id, username)
                    )
                    await db.commit()
                await update.message.reply_text(
                    "Login realizado com sucesso! Use /start para continuar."
                )
            else:
                await update.message.reply_text(
                    "Usuário ou senha incorretos. Tente novamente."
                )
        except httpx.HTTPError:
            await update.message.reply_text("Erro ao conectar com a API.")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

async def meal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text(
            "Você precisa estar logado para usar este comando. Use /login ou /signup."
        )
        return
    await update.message.reply_text("Registre sua refeição: /meals breakfast 1 100")

async def goal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text(
            "Você precisa estar logado para usar este comando. Use /login ou /signup."
        )
        return
    await update.message.reply_text("Defina sua meta: /goals energy_kcal 2000")

async def water_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text(
            "Você precisa estar logado para usar este comando. Use /login ou /signup."
        )
        return
    await update.message.reply_text("Registre água consumida: /water 2000")

async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text(
            "Você precisa estar logado para usar este comando. Use /login ou /signup."
        )
        return
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/summary/{update.effective_user.id}",
                headers={"Authorization": f"Bearer {context.user_data.get('access_token')}"}
            )
            if response.status_code == 200:
                summary = response.json()
                await update.message.reply_text(summary['text'], parse_mode='Markdown')
            else:
                await update.message.reply_text("Erro ao obter resumo.")
        except httpx.HTTPError:
            await update.message.reply_text("Erro ao conectar com a API.")

async def calc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text(
            "Você precisa estar logado para usar este comando. Use /login ou /signup."
        )
        return
    await update.message.reply_text("Realize um cálculo: /calculations imc 70 175")

async def reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_user_authenticated(update.effective_user.id):
        await update.message.reply_text(
            "Você precisa estar logado para usar este comando. Use /login ou /signup."
        )
        return
    await update.message.reply_text("Configure um lembrete: /reminders meal_reminder 12:00")

async def tips_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/tips")
            if response.status_code == 200:
                tip = response.json().get("tip")
                await update.message.reply_text(f"Dica do dia: {tip}")
            else:
                await update.message.reply_text("Não foi possível obter a dica do dia.")
        except httpx.HTTPError:
            await update.message.reply_text("Erro ao conectar com a API.")
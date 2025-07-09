import json
import logging
import aiosqlite
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from dotenv import load_dotenv
import os
import asyncio
from aiohttp import web

# Carregar variáveis de ambiente
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
# Ex.: https://seu-ngrok-id.ngrok-free.app/webhook
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443)
                   )  # Porta padrão para webhook

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar dados de alimentos do JSON
with open('tabela_alimentos.json', 'r', encoding='utf-8') as f:
    food_data = json.load(f)

# Estados da conversa
TIPO_REFEICAO, SELECAO_ALIMENTO, QUANTIDADE, CONFIRMAR = range(4)
TIPO_META, VALOR_META = range(2, 4)
QUANTIDADE_AGUA = 0

# Traduções para português
translations = {
    'pt': {
        'welcome': 'Bem-vindo ao NutriBot! Escolha uma opção:',
        'select_meal': 'Selecione o tipo de refeição:',
        'select_food': 'Selecione um alimento:',
        'enter_quantity': 'Digite a quantidade (gramas):',
        'confirm_meal': 'Confirmar: {quantity}g de {food} para {meal_type}?\nResponda "sim" ou "não".',
        'meal_registered': 'Refeição registrada com sucesso!',
        'meal_cancelled': 'Registro de refeição cancelado.',
        'no_meals': 'Nenhuma refeição registrada hoje.',
        'daily_summary': 'Resumo Diário ({date}):\n',
        'goals_progress': '\nProgresso das Metas:\n',
        'select_nutrient': 'Selecione o nutriente para definir a meta:',
        'enter_goal': 'Digite a meta para {nutrient}:',
        'goal_set': 'Meta para {nutrient} definida como {value}.',
        'enter_water': 'Digite a quantidade de água (ml):',
        'water_added': 'Adicionado {amount}ml de água. Total hoje: {total}ml',
        'invalid_number': 'Por favor, digite um número válido.',
        'positive_number': 'Por favor, digite um número positivo.',
        'no_foods_found': 'Nenhum alimento encontrado. Tente outro termo.',
        'action_cancelled': 'Ação cancelada.',
        'search_prompt': 'Digite o nome do alimento para buscar:'
    }
}

# Funções auxiliares


def get_food_nutrients(food_id, quantity):
    """Calcula nutrientes para um alimento e quantidade."""
    for food in food_data:
        if food['id'] == food_id:
            factor = quantity / 100  # Ajusta para quantidade em gramas
            return {
                'description': food['description'],
                'energy_kcal': float(food['energy_kcal']) * factor if food['energy_kcal'] != 'NA' else 0,
                'protein_g': float(food['protein_g']) * factor if food['protein_g'] != 'NA' else 0,
                'lipid_g': float(food['lipid_g']) * factor if food['lipid_g'] != 'NA' else 0,
                'carbohydrate_g': float(food['carbohydrate_g']) * factor if food['carbohydrate_g'] != 'NA' else 0,
                'fiber_g': float(food['fiber_g']) * factor if food['fiber_g'] != 'NA' else 0
            }
    return None


async def init_db():
    """Inicializa o banco de dados SQLite."""
    async with aiosqlite.connect('nutribot.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS meals
                            (user_id INTEGER, meal_type TEXT, food_id INTEGER, quantity REAL, timestamp TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS goals
                            (user_id INTEGER, nutrient TEXT, value REAL)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS water
                            (user_id INTEGER, amount REAL, date TEXT)''')
        await db.commit()


async def save_meal(user_id, meal_type, food_id, quantity):
    """Salva uma refeição no banco de dados."""
    async with aiosqlite.connect('nutribot.db') as db:
        await db.execute('INSERT INTO meals (user_id, meal_type, food_id, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
                         (user_id, meal_type, food_id, quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        await db.commit()


async def get_daily_summary(user_id):
    """Gera um resumo nutricional diário."""
    total = {'energy_kcal': 0, 'protein_g': 0,
             'lipid_g': 0, 'carbohydrate_g': 0, 'fiber_g': 0}
    async with aiosqlite.connect('nutribot.db') as db:
        cursor = await db.execute('SELECT food_id, quantity FROM meals WHERE user_id = ? AND date(timestamp) = ?',
                                  (user_id, datetime.now().strftime('%Y-%m-%d')))
        meals = await cursor.fetchall()
        if not meals:
            return translations['pt']['no_meals']

        for food_id, quantity in meals:
            nutrients = get_food_nutrients(food_id, quantity)
            if nutrients:
                for key in total:
                    total[key] += nutrients[key]

        summary = translations['pt']['daily_summary'].format(
            date=datetime.now().strftime('%Y-%m-%d'))
        for key, value in total.items():
            summary += f"{key.replace('_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')}: {value:.1f}\n"

        cursor = await db.execute('SELECT nutrient, value FROM goals WHERE user_id = ?', (user_id,))
        goals = await cursor.fetchall()
        if goals:
            summary += translations['pt']['goals_progress']
            for nutrient, goal in goals:
                current = total.get(nutrient, 0)
                summary += f"{nutrient.replace('_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')}: {current:.1f}/{goal:.1f}\n"

        return summary

# Comandos do bot


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o bot e exibe o menu principal."""
    keyboard = [
        [InlineKeyboardButton("Registrar Refeição",
                              callback_data='register_meal')],
        [InlineKeyboardButton("Ver Resumo", callback_data='summary')],
        [InlineKeyboardButton("Definir Metas", callback_data='set_goals')],
        [InlineKeyboardButton("Rastrear Água", callback_data='track_water')],
        [InlineKeyboardButton("Dicas Saudáveis", callback_data='tips')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(translations['pt']['welcome'], reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com cliques nos botões."""
    query = update.callback_query
    await query.answer()

    if query.data == 'register_meal':
        keyboard = [
            [InlineKeyboardButton("Café da Manhã", callback_data='breakfast')],
            [InlineKeyboardButton("Almoço", callback_data='lunch')],
            [InlineKeyboardButton(
                "Lanche da Tarde", callback_data='afternoon_snack')],
            [InlineKeyboardButton("Jantar", callback_data='dinner')],
            [InlineKeyboardButton("Ceia", callback_data='supper')],
            [InlineKeyboardButton("Cancelar", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(translations['pt']['select_meal'], reply_markup=reply_markup)
        return TIPO_REFEICAO
    elif query.data == 'summary':
        summary = await get_daily_summary(query.from_user.id)
        await query.message.reply_text(summary)
    elif query.data == 'set_goals':
        keyboard = [
            [InlineKeyboardButton(
                "Calorias", callback_data='goal_energy_kcal')],
            [InlineKeyboardButton(
                "Proteínas", callback_data='goal_protein_g')],
            [InlineKeyboardButton(
                "Carboidratos", callback_data='goal_carbohydrate_g')],
            [InlineKeyboardButton("Lipídios", callback_data='goal_lipid_g')],
            [InlineKeyboardButton("Fibras", callback_data='goal_fiber_g')],
            [InlineKeyboardButton("Cancelar", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(translations['pt']['select_nutrient'], reply_markup=reply_markup)
        return TIPO_META
    elif query.data == 'track_water':
        await query.message.reply_text(translations['pt']['enter_water'])
        return QUANTIDADE_AGUA
    elif query.data == 'tips':
        tips = [
            "Inclua grãos integrais como aveia para mais fibras!",
            "Nozes como amêndoas são ótimas para gorduras saudáveis.",
            "Mantenha-se hidratado: busque 2L de água por dia.",
            "Experimente adicionar soja para proteína vegetal."
        ]
        await query.message.reply_text(tips[datetime.now().day % len(tips)])
    elif query.data == 'cancel':
        await query.message.reply_text(translations['pt']['action_cancelled'])
        return ConversationHandler.END

# Conversa para registro de refeições


async def meal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seleciona o tipo de refeição."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['meal_cancelled'])
        return ConversationHandler.END

    context.user_data['meal_type'] = query.data
    keyboard = [
        [InlineKeyboardButton(food['description'],
                              callback_data=str(food['id']))]
        # Mostra primeiros 5 alimentos para simplicidade
        for food in food_data[:5]
    ]
    keyboard.append([InlineKeyboardButton(
        "Buscar Alimento", callback_data='search_food')])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data='cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(translations['pt']['select_food'], reply_markup=reply_markup)
    return SELECAO_ALIMENTO


async def search_food_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia a busca de alimentos."""
    await update.message.reply_text(translations['pt']['search_prompt'])
    return SELECAO_ALIMENTO


async def search_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca alimentos com base no texto digitado."""
    query = update.message.text.lower()
    matches = [food for food in food_data if query in food['description'].lower()]
    if not matches:
        await update.message.reply_text(translations['pt']['no_foods_found'])
        return SELECAO_ALIMENTO
    keyboard = [[InlineKeyboardButton(
        food['description'], callback_data=str(food['id']))] for food in matches[:10]]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data='cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(translations['pt']['select_food'], reply_markup=reply_markup)
    return SELECAO_ALIMENTO


async def food_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seleciona um alimento da lista."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['meal_cancelled'])
        return ConversationHandler.END
    elif query.data == 'search_food':
        await query.message.reply_text(translations['pt']['search_prompt'])
        return SELECAO_ALIMENTO

    context.user_data['food_id'] = int(query.data)
    await query.message.reply_text(translations['pt']['enter_quantity'])
    return QUANTIDADE


async def quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra a quantidade do alimento."""
    try:
        quantity = float(update.message.text)
        if quantity <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return QUANTIDADE
        context.user_data['quantity'] = quantity
        food = next(
            f for f in food_data if f['id'] == context.user_data['food_id'])
        await update.message.reply_text(
            translations['pt']['confirm_meal'].format(
                quantity=quantity,
                food=food['description'],
                meal_type=context.user_data['meal_type']
            )
        )
        return CONFIRMAR
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return QUANTIDADE


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirma o registro da refeição."""
    response = update.message.text.lower()
    if response == 'sim':
        await save_meal(
            update.message.from_user.id,
            context.user_data['meal_type'],
            context.user_data['food_id'],
            context.user_data['quantity']
        )
        await update.message.reply_text(translations['pt']['meal_registered'])
    else:
        await update.message.reply_text(translations['pt']['meal_cancelled'])
    return ConversationHandler.END

# Conversa para definir metas


async def goal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seleciona o tipo de nutriente para a meta."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['action_cancelled'])
        return ConversationHandler.END

    context.user_data['goal_type'] = query.data.replace('goal_', '')
    await query.message.reply_text(
        translations['pt']['enter_goal'].format(
            nutrient=context.user_data['goal_type'].replace(
                '_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')
        )
    )
    return VALOR_META


async def goal_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define o valor da meta."""
    try:
        value = float(update.message.text)
        if value <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return VALOR_META
        user_id = update.message.from_user.id
        async with aiosqlite.connect('nutribot.db') as db:
            await db.execute('INSERT OR REPLACE INTO goals (user_id, nutrient, value) VALUES (?, ?, ?)',
                             (user_id, context.user_data['goal_type'], value))
            await db.commit()
        await update.message.reply_text(
            translations['pt']['goal_set'].format(
                nutrient=context.user_data['goal_type'].replace(
                    '_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)'),
                value=value
            )
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return VALOR_META

# Rastreamento de água


async def track_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra o consumo de água."""
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return QUANTIDADE_AGUA
        user_id = update.message.from_user.id
        today = datetime.now().strftime('%Y-%m-%d')
        async with aiosqlite.connect('nutribot.db') as db:
            await db.execute('INSERT INTO water (user_id, amount, date) VALUES (?, ?, ?)',
                             (user_id, amount, today))
            await db.commit()
            cursor = await db.execute('SELECT SUM(amount) FROM water WHERE user_id = ? AND date = ?',
                                      (user_id, today))
            total = (await cursor.fetchone())[0] or 0
        await update.message.reply_text(translations['pt']['water_added'].format(amount=amount, total=total))
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return QUANTIDADE_AGUA


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela a ação atual."""
    await update.message.reply_text(translations['pt']['action_cancelled'])
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com erros do bot."""
    logger.warning('Atualização "%s" causou erro "%s"', update, context.error)


async def webhook_handler(request, application):
    """Lida com requisições webhook recebidas do Telegram."""
    try:
        update = Update.de_json(await request.json(), application.bot)
        if update:
            await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Erro ao processar atualização do webhook: {e}")
        return web.Response(status=500)


async def main():
    """Função principal para iniciar o bot no modo webhook com aiohttp."""
    if not BOT_TOKEN:
        raise ValueError(
            "O token do bot não foi encontrado. Verifique o arquivo .env.")
    if not WEBHOOK_URL:
        raise ValueError(
            "A URL do webhook não foi encontrada. Verifique o arquivo .env.")

    await init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversa para registro de refeições
    meal_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                meal_type, pattern='^(breakfast|lunch|afternoon_snack|dinner|supper)$'),
            CommandHandler('buscar', search_food_command)
        ],
        states={
            TIPO_REFEICAO: [CallbackQueryHandler(meal_type)],
            SELECAO_ALIMENTO: [CallbackQueryHandler(food_selection), MessageHandler(filters.TEXT & ~filters.COMMAND, search_food)],
            QUANTIDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity)],
            CONFIRMAR: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, confirm)]
        },
        fallbacks=[CommandHandler('cancelar', cancel)]
    )

    # Conversa para definir metas
    goal_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(goal_type, pattern='^goal_')],
        states={
            TIPO_META: [CallbackQueryHandler(goal_type)],
            VALOR_META: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, goal_value)]
        },
        fallbacks=[CommandHandler('cancelar', cancel)]
    )

    # Conversa para rastreamento de água
    water_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern='^track_water$')],
        states={
            QUANTIDADE_AGUA: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, track_water)]
        },
        fallbacks=[CommandHandler('cancelar', cancel)]
    )

    # Adicionar manipuladores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(meal_conv)
    application.add_handler(goal_conv)
    application.add_handler(water_conv)
    application.add_handler(CallbackQueryHandler(button))
    application.add_error_handler(error_handler)

    # Configurar o servidor aiohttp
    app = web.Application()
    app.router.add_post(
        '/webhook', lambda request: webhook_handler(request, application))

    try:
        # Inicializar o bot e configurar o webhook
        await application.initialize()
        await application.bot.set_webhook(url=WEBHOOK_URL)
        await application.start()

        # Iniciar o servidor aiohttp
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
        await site.start()

        logger.info(
            f"Servidor webhook iniciado em http://0.0.0.0:{WEBHOOK_PORT}")
        logger.info(f"Webhook configurado para {WEBHOOK_URL}")

        # Manter o servidor rodando
        while True:
            await asyncio.sleep(3600)  # Dormir por 1 hora
    except asyncio.CancelledError:
        pass
    finally:
        # Limpar recursos
        await application.stop()
        await application.bot.delete_webhook()
        await application.shutdown()
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())

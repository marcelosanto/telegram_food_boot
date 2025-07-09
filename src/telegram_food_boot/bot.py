import json
import logging
import aiosqlite
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    JobQueue,
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
CALCULADORA, PESO_IMC, ALTURA_IMC, PESO_TMB, ALTURA_TMB, IDADE_TMB, SEXO_TMB, NIVEL_ATIVIDADE_TMB, PESO_FAT, IDADE_FAT, SEXO_FAT = range(
    7, 18)
LEMBRETE_TIPO, LEMBRETE_HORARIO = range(18, 20)

# Traduções para português
translations = {
    'pt': {
        'welcome': '🌟 *Bem-vindo ao NutriBot!* 🌟\nEscolha uma opção abaixo:',
        'select_meal': '🍽️ Selecione o tipo de refeição:',
        'select_food': '🥗 Selecione um alimento:',
        'enter_quantity': '📏 Digite a quantidade (gramas):',
        'confirm_meal': '✅ Confirmar: {quantity}g de *{food}* para *{meal_type}*?\nResponda "sim" ou "não".',
        'meal_registered': '🎉 Refeição registrada com sucesso!',
        'meal_cancelled': '❌ Registro de refeição cancelado.',
        'no_meals': '😕 Nenhuma refeição registrada hoje.',
        'daily_summary': '📊 *Resumo Diário ({date})*\n\n',
        'meals_summary': '🍽️ *Refeições do Dia*\n',
        'goals_progress': '\n🎯 *Progresso das Metas*\n',
        'water_summary': '\n💧 *Consumo de Água*\n',
        'calculations_summary': '\n🧮 *Últimos Cálculos*\n',
        'select_nutrient': '🎯 Selecione o nutriente para definir a meta:',
        'enter_goal': '📈 Digite a meta para *{nutrient}*:',
        'goal_set': '✅ Meta para *{nutrient}* definida como {value}.',
        'enter_water': '💧 Digite a quantidade de água (ml):',
        'water_added': '💦 Adicionado {amount}ml de água. Total hoje: *{total}ml*',
        'invalid_number': '⚠️ Por favor, digite um número válido.',
        'positive_number': '⚠️ Por favor, digite um número positivo.',
        'no_foods_found': '🔍 Nenhum alimento encontrado. Tente outro termo.',
        'action_cancelled': '❌ Ação cancelada.',
        'search_prompt': '🔍 Digite o nome do alimento para buscar:',
        'select_calculator': '🧮 Selecione uma calculadora:',
        'enter_weight_imc': '⚖️ Digite seu peso (kg):',
        'enter_height_imc': '📏 Digite sua altura (cm):',
        'imc_result': '✅ Seu IMC é *{imc:.1f}* ({category}).\nInterpretação: {interpretation}',
        'enter_weight_tmb': '⚖️ Digite seu peso (kg):',
        'enter_height_tmb': '📏 Digite sua altura (cm):',
        'enter_age_tmb': '🎂 Digite sua idade (anos):',
        'select_gender_tmb': '🚻 Selecione seu sexo:',
        'select_activity_level': '🏃 Selecione seu nível de atividade:',
        'tmb_result': '🔥 Sua TMB é *{tmb:.0f} kcal/dia*.\nIsso representa as calorias que seu corpo queima em repouso.',
        'tdee_result': '⚡ Seu TDEE é *{tdee:.0f} kcal/dia*.\nIsso estima as calorias que você queima com base no seu nível de atividade ({activity_level}).',
        'enter_weight_fat': '⚖️ Digite seu peso (kg):',
        'enter_age_fat': '🎂 Digite sua idade (anos):',
        'select_gender_fat': '🚻 Selecione seu sexo:',
        'fat_percentage_result': '📊 Seu percentual de gordura corporal estimado é *{fat:.1f}%*.\nNota: Esta é uma estimativa baseada na fórmula de Deurenberg.',
        'select_reminder_type': '⏰ Selecione o tipo de lembrete:',
        'enter_reminder_time': '🕒 Digite o horário do lembrete (formato HH:MM, ex.: 08:00):',
        'reminder_set': '✅ Lembrete de *{type}* configurado para *{time}*!',
        'invalid_time': '⚠️ Formato de horário inválido. Use HH:MM (ex.: 08:00).',
        'reminder_meal': '🍽️ Hora de registrar sua refeição! Use /start para começar.',
        'reminder_water': '💧 Hora de se hidratar! Registre sua água com /start.'
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


def calculate_imc(weight, height):
    """Calcula o IMC e retorna o valor, categoria e interpretação."""
    height_m = height / 100  # Converter cm para metros
    imc = weight / (height_m ** 2)
    if imc < 18.5:
        category = "Abaixo do peso"
        interpretation = "Você está abaixo do peso ideal. Considere consultar um nutricionista."
    elif 18.5 <= imc < 25:
        category = "Peso normal"
        interpretation = "Seu peso está na faixa considerada saudável."
    elif 25 <= imc < 30:
        category = "Sobrepeso"
        interpretation = "Você está com sobrepeso. Uma dieta equilibrada pode ajudar."
    elif 30 <= imc < 35:
        category = "Obesidade grau I"
        interpretation = "Você está no grau I de obesidade. Consulte um profissional."
    elif 35 <= imc < 40:
        category = "Obesidade grau II"
        interpretation = "Você está no grau II de obesidade. Atenção à saúde é importante."
    else:
        category = "Obesidade grau III"
        interpretation = "Você está no grau III de obesidade. Busque orientação médica."
    return imc, category, interpretation


def calculate_tmb(weight, height, age, gender):
    """Calcula a TMB usando a equação de Mifflin-St Jeor."""
    if gender == 'male':
        tmb = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # female
        tmb = 10 * weight + 6.25 * height - 5 * age - 161
    return tmb


def calculate_tdee(tmb, activity_level):
    """Calcula o TDEE com base na TMB e no nível de atividade."""
    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }
    return tmb * activity_multipliers[activity_level]


def calculate_fat_percentage(imc, age, gender):
    """Estima o percentual de gordura corporal usando a fórmula de Deurenberg."""
    if gender == 'male':
        fat = 1.2 * imc + 0.23 * age - 10.8 - 5.4
    else:  # female
        fat = 1.2 * imc + 0.23 * age - 5.4
    return max(fat, 0)  # Garante que o valor não seja negativo


async def init_db():
    """Inicializa o banco de dados SQLite."""
    async with aiosqlite.connect('nutribot.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS meals
                            (user_id INTEGER, meal_type TEXT, food_id INTEGER, quantity REAL, timestamp TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS goals
                            (user_id INTEGER, nutrient TEXT, value REAL)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS water
                            (user_id INTEGER, amount REAL, date TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS calculations
                            (user_id INTEGER, type TEXT, result REAL, details TEXT, timestamp TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS reminders
                            (user_id INTEGER, type TEXT, time TEXT)''')
        await db.commit()


async def save_meal(user_id, meal_type, food_id, quantity):
    """Salva uma refeição no banco de dados."""
    async with aiosqlite.connect('nutribot.db') as db:
        await db.execute('INSERT INTO meals (user_id, meal_type, food_id, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
                         (user_id, meal_type, food_id, quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        await db.commit()


async def save_calculation(user_id, calc_type, result, details):
    """Salva um cálculo (IMC, TMB, TDEE, Fat) no banco de dados."""
    async with aiosqlite.connect('nutribot.db') as db:
        await db.execute('INSERT INTO calculations (user_id, type, result, details, timestamp) VALUES (?, ?, ?, ?, ?)',
                         (user_id, calc_type, result, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        await db.commit()


async def save_reminder(user_id, reminder_type, time):
    """Salva um lembrete no banco de dados."""
    async with aiosqlite.connect('nutribot.db') as db:
        await db.execute('INSERT OR REPLACE INTO reminders (user_id, type, time) VALUES (?, ?, ?)',
                         (user_id, reminder_type, time))
        await db.commit()


async def get_daily_summary(user_id):
    """Gera um resumo nutricional diário detalhado."""
    summary = translations['pt']['daily_summary'].format(
        date=datetime.now().strftime('%Y-%m-%d'))

    # Resumo das refeições
    total = {'energy_kcal': 0, 'protein_g': 0,
             'lipid_g': 0, 'carbohydrate_g': 0, 'fiber_g': 0}
    async with aiosqlite.connect('nutribot.db') as db:
        cursor = await db.execute('SELECT meal_type, food_id, quantity, timestamp FROM meals WHERE user_id = ? AND date(timestamp) = ?',
                                  (user_id, datetime.now().strftime('%Y-%m-%d')))
        meals = await cursor.fetchall()
        if meals:
            summary += translations['pt']['meals_summary']
            for meal_type, food_id, quantity, timestamp in meals:
                nutrients = get_food_nutrients(food_id, quantity)
                if nutrients:
                    summary += f"• *{meal_type.capitalize()}* às {timestamp.split(' ')[1]}: {nutrients['description']} ({quantity}g)\n"
                    summary += f"  Calorias: {nutrients['energy_kcal']:.1f} kcal, Proteínas: {nutrients['protein_g']:.1f}g, Carboidratos: {nutrients['carbohydrate_g']:.1f}g, Lipídios: {nutrients['lipid_g']:.1f}g, Fibras: {nutrients['fiber_g']:.1f}g\n"
                    for key in total:
                        total[key] += nutrients[key]
            summary += "\n*Totais do Dia*\n"
            for key, value in total.items():
                summary += f"• {key.replace('_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')}: *{value:.1f}*\n"
        else:
            summary += translations['pt']['no_meals'] + "\n"

        # Progresso das metas
        cursor = await db.execute('SELECT nutrient, value FROM goals WHERE user_id = ?', (user_id,))
        goals = await cursor.fetchall()
        if goals:
            summary += translations['pt']['goals_progress']
            for nutrient, goal in goals:
                current = total.get(nutrient, 0)
                percentage = (current / goal * 100) if goal > 0 else 0
                summary += f"• {nutrient.replace('_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')}: *{current:.1f}/{goal:.1f}* ({percentage:.1f}%)\n"

        # Consumo de água
        cursor = await db.execute('SELECT SUM(amount) FROM water WHERE user_id = ? AND date = ?',
                                  (user_id, datetime.now().strftime('%Y-%m-%d')))
        total_water = (await cursor.fetchone())[0] or 0
        summary += translations['pt']['water_summary']
        summary += f"• Total: *{total_water:.0f}ml*\n"

        # Últimos cálculos
        cursor = await db.execute('SELECT type, result, details FROM calculations WHERE user_id = ? ORDER BY timestamp DESC LIMIT 2',
                                  (user_id,))
        calculations = await cursor.fetchall()
        if calculations:
            summary += translations['pt']['calculations_summary']
            for calc_type, result, details in calculations:
                summary += f"• {calc_type}: *{result:.1f}* ({details})\n"

    return summary

# Comandos do bot


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o bot e exibe o menu principal."""
    # Limpar qualquer estado de conversa ativo
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("Registrar Refeição",
                              callback_data='register_meal')],
        [InlineKeyboardButton("Ver Resumo", callback_data='summary')],
        [InlineKeyboardButton("Definir Metas", callback_data='set_goals')],
        [InlineKeyboardButton("Rastrear Água", callback_data='track_water')],
        [InlineKeyboardButton("Dicas Saudáveis", callback_data='tips')],
        [InlineKeyboardButton("Calculadoras", callback_data='calculators')],
        [InlineKeyboardButton("Configurar Lembretes",
                              callback_data='set_reminder')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.info(
        f"Enviando menu principal para user_id {update.effective_user.id} com {len(keyboard)} botões")
    await update.message.reply_text(translations['pt']['welcome'], reply_markup=reply_markup, parse_mode='Markdown')
    # Não retornar ConversationHandler.END para evitar interferência


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
        await query.message.reply_text(summary, parse_mode='Markdown')
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
            "🌾 Inclua grãos integrais como aveia para mais fibras!",
            "🥜 Nozes como amêndoas são ótimas para gorduras saudáveis.",
            "💧 Mantenha-se hidratado: busque 2L de água por dia.",
            "🌱 Experimente adicionar soja para proteína vegetal."
        ]
        await query.message.reply_text(tips[datetime.now().day % len(tips)], parse_mode='Markdown')
    elif query.data == 'calculators':
        keyboard = [
            [InlineKeyboardButton("Calcular IMC", callback_data='calc_imc')],
            [InlineKeyboardButton("Calcular TMB", callback_data='calc_tmb')],
            [InlineKeyboardButton("Calcular TDEE", callback_data='calc_tdee')],
            [InlineKeyboardButton("Calcular % de Gordura",
                                  callback_data='calc_fat')],
            [InlineKeyboardButton("Cancelar", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(translations['pt']['select_calculator'], reply_markup=reply_markup)
        return CALCULADORA
    elif query.data == 'set_reminder':
        keyboard = [
            [InlineKeyboardButton("Lembrete de Refeição",
                                  callback_data='meal_reminder')],
            [InlineKeyboardButton("Lembrete de Água",
                                  callback_data='water_reminder')],
            [InlineKeyboardButton("Cancelar", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(translations['pt']['select_reminder_type'], reply_markup=reply_markup)
        return LEMBRETE_TIPO
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
            ),
            parse_mode='Markdown'
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
        await update.message.reply_text(translations['pt']['meal_registered'], parse_mode='Markdown')
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
        ),
        parse_mode='Markdown'
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
            ),
            parse_mode='Markdown'
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
        await update.message.reply_text(translations['pt']['water_added'].format(amount=amount, total=total), parse_mode='Markdown')
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return QUANTIDADE_AGUA

# Conversa para calculadoras


async def calculator_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seleciona o tipo de calculadora."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['action_cancelled'])
        return ConversationHandler.END

    context.user_data['calc_type'] = query.data
    if query.data == 'calc_imc':
        await query.message.reply_text(translations['pt']['enter_weight_imc'])
        return PESO_IMC
    elif query.data == 'calc_tmb':
        await query.message.reply_text(translations['pt']['enter_weight_tmb'])
        return PESO_TMB
    elif query.data == 'calc_tdee':
        await query.message.reply_text(translations['pt']['enter_weight_tmb'])
        return PESO_TMB
    elif query.data == 'calc_fat':
        await query.message.reply_text(translations['pt']['enter_weight_fat'])
        return PESO_FAT


async def peso_imc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra o peso para o cálculo do IMC."""
    try:
        weight = float(update.message.text)
        if weight <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return PESO_IMC
        context.user_data['weight'] = weight
        await update.message.reply_text(translations['pt']['enter_height_imc'])
        return ALTURA_IMC
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return PESO_IMC


async def altura_imc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra a altura para o cálculo do IMC."""
    try:
        height = float(update.message.text)
        if height <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return ALTURA_IMC
        context.user_data['height'] = height
        imc, category, interpretation = calculate_imc(
            context.user_data['weight'], context.user_data['height'])
        await save_calculation(
            update.message.from_user.id,
            'IMC',
            imc,
            f"Peso: {context.user_data['weight']}kg, Altura: {context.user_data['height']}cm, Categoria: {category}"
        )
        await update.message.reply_text(
            translations['pt']['imc_result'].format(
                imc=imc, category=category, interpretation=interpretation),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return ALTURA_IMC


async def peso_tmb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra o peso para o cálculo da TMB ou TDEE."""
    try:
        weight = float(update.message.text)
        if weight <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return PESO_TMB
        context.user_data['weight'] = weight
        await update.message.reply_text(translations['pt']['enter_height_tmb'])
        return ALTURA_TMB
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return PESO_TMB


async def altura_tmb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra a altura para o cálculo da TMB ou TDEE."""
    try:
        height = float(update.message.text)
        if height <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return ALTURA_TMB
        context.user_data['height'] = height
        await update.message.reply_text(translations['pt']['enter_age_tmb'])
        return IDADE_TMB
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return ALTURA_TMB


async def idade_tmb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra a idade para o cálculo da TMB ou TDEE."""
    try:
        age = float(update.message.text)
        if age <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return IDADE_TMB
        context.user_data['age'] = age
        keyboard = [
            [InlineKeyboardButton("Masculino", callback_data='male')],
            [InlineKeyboardButton("Feminino", callback_data='female')],
            [InlineKeyboardButton("Cancelar", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(translations['pt']['select_gender_tmb'], reply_markup=reply_markup)
        return SEXO_TMB
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return IDADE_TMB


async def sexo_tmb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra o sexo para o cálculo da TMB ou TDEE."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['action_cancelled'])
        return ConversationHandler.END

    context.user_data['gender'] = query.data
    tmb = calculate_tmb(
        context.user_data['weight'],
        context.user_data['height'],
        context.user_data['age'],
        context.user_data['gender']
    )
    if context.user_data['calc_type'] == 'calc_tmb':
        await save_calculation(
            query.from_user.id,
            'TMB',
            tmb,
            f"Peso: {context.user_data['weight']}kg, Altura: {context.user_data['height']}cm, Idade: {context.user_data['age']} anos, Sexo: {context.user_data['gender']}"
        )
        await query.message.reply_text(
            translations['pt']['tmb_result'].format(tmb=tmb),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    else:  # calc_tdee
        keyboard = [
            [InlineKeyboardButton("Sedentário", callback_data='sedentary')],
            [InlineKeyboardButton("Leve", callback_data='light')],
            [InlineKeyboardButton("Moderado", callback_data='moderate')],
            [InlineKeyboardButton("Ativo", callback_data='active')],
            [InlineKeyboardButton("Muito Ativo", callback_data='very_active')],
            [InlineKeyboardButton("Cancelar", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(translations['pt']['select_activity_level'], reply_markup=reply_markup)
        return NIVEL_ATIVIDADE_TMB


async def nivel_atividade_tmb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra o nível de atividade para o cálculo do TDEE."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['action_cancelled'])
        return ConversationHandler.END

    activity_level = query.data
    tmb = calculate_tmb(
        context.user_data['weight'],
        context.user_data['height'],
        context.user_data['age'],
        context.user_data['gender']
    )
    tdee = calculate_tdee(tmb, activity_level)
    activity_labels = {
        'sedentary': 'Sedentário (pouco ou nenhum exercício)',
        'light': 'Leve (exercício leve 1-3 dias/semana)',
        'moderate': 'Moderado (exercício moderado 3-5 dias/semana)',
        'active': 'Ativo (exercício intenso 6-7 dias/semana)',
        'very_active': 'Muito Ativo (exercício muito intenso ou trabalho físico)'
    }
    await save_calculation(
        query.from_user.id,
        'TDEE',
        tdee,
        f"Peso: {context.user_data['weight']}kg, Altura: {context.user_data['height']}cm, Idade: {context.user_data['age']} anos, Sexo: {context.user_data['gender']}, Nível de Atividade: {activity_labels[activity_level]}"
    )
    await query.message.reply_text(
        translations['pt']['tdee_result'].format(
            tdee=tdee, activity_level=activity_labels[activity_level]),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def peso_fat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra o peso para o cálculo do percentual de gordura."""
    try:
        weight = float(update.message.text)
        if weight <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return PESO_FAT
        context.user_data['weight'] = weight
        await update.message.reply_text(translations['pt']['enter_age_fat'])
        return IDADE_FAT
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return PESO_FAT


async def idade_fat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra a idade para o cálculo do percentual de gordura."""
    try:
        age = float(update.message.text)
        if age <= 0:
            await update.message.reply_text(translations['pt']['positive_number'])
            return IDADE_FAT
        context.user_data['age'] = age
        keyboard = [
            [InlineKeyboardButton("Masculino", callback_data='male')],
            [InlineKeyboardButton("Feminino", callback_data='female')],
            [InlineKeyboardButton("Cancelar", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(translations['pt']['select_gender_fat'], reply_markup=reply_markup)
        return SEXO_FAT
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_number'])
        return IDADE_FAT


async def sexo_fat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra o sexo para o cálculo do percentual de gordura."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['action_cancelled'])
        return ConversationHandler.END

    context.user_data['gender'] = query.data
    imc, _, _ = calculate_imc(context.user_data['weight'], context.user_data.get(
        'height', 170))  # Usa altura padrão se não disponível
    fat = calculate_fat_percentage(
        imc, context.user_data['age'], context.user_data['gender'])
    await save_calculation(
        query.from_user.id,
        'Fat Percentage',
        fat,
        f"Peso: {context.user_data['weight']}kg, Idade: {context.user_data['age']} anos, Sexo: {context.user_data['gender']}"
    )
    await query.message.reply_text(
        translations['pt']['fat_percentage_result'].format(fat=fat),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# Conversa para lembretes


async def reminder_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seleciona o tipo de lembrete."""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text(translations['pt']['action_cancelled'])
        return ConversationHandler.END

    context.user_data['reminder_type'] = query.data
    await query.message.reply_text(translations['pt']['enter_reminder_time'])
    return LEMBRETE_HORARIO


async def reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configura o horário do lembrete."""
    try:
        time_str = update.message.text
        # Valida formato HH:MM
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        user_id = update.message.from_user.id
        reminder_type = context.user_data['reminder_type']
        await save_reminder(user_id, reminder_type, time_str)

        # Agendar lembrete
        job_queue = context.job_queue
        t = datetime.strptime(time_str, '%H:%M').time()
        now = datetime.now()
        first_run = now.replace(
            hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if first_run < now:
            first_run += timedelta(days=1)

        async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
            reminder_type = context.job.data['type']
            message = translations['pt']['reminder_meal'] if reminder_type == 'meal_reminder' else translations['pt']['reminder_water']
            await context.bot.send_message(chat_id=context.job.data['user_id'], text=message, parse_mode='Markdown')

        job_queue.run_daily(
            callback=send_reminder,
            time=first_run,
            data={'user_id': user_id, 'type': reminder_type},
            name=f"{reminder_type}_{user_id}"
        )

        await update.message.reply_text(
            translations['pt']['reminder_set'].format(
                type='Refeição' if reminder_type == 'meal_reminder' else 'Água',
                time=time_str
            ),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(translations['pt']['invalid_time'])
        return LEMBRETE_HORARIO


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


async def setup_reminders(application: Application):
    """Configura lembretes salvos no banco de dados ao iniciar o bot."""
    async with aiosqlite.connect('nutribot.db') as db:
        cursor = await db.execute('SELECT user_id, type, time FROM reminders')
        reminders = await cursor.fetchall()

    job_queue = application.job_queue
    for user_id, reminder_type, time_str in reminders:
        async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
            reminder_type = context.job.data['type']
            message = translations['pt']['reminder_meal'] if reminder_type == 'meal_reminder' else translations['pt']['reminder_water']
            await context.bot.send_message(chat_id=context.job.data['user_id'], text=message, parse_mode='Markdown')

        t = datetime.strptime(time_str, '%H:%M').time()
        now = datetime.now()
        first_run = now.replace(
            hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if first_run < now:
            first_run += timedelta(days=1)

        job_queue.run_daily(
            callback=send_reminder,
            time=first_run,
            data={'user_id': user_id, 'type': reminder_type},
            name=f"{reminder_type}_{user_id}"
        )


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

    # Conversa para calculadoras
    calc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            calculator_type, pattern='^(calc_imc|calc_tmb|calc_tdee|calc_fat)$')],
        states={
            CALCULADORA: [CallbackQueryHandler(calculator_type)],
            PESO_IMC: [MessageHandler(filters.TEXT & ~filters.COMMAND, peso_imc)],
            ALTURA_IMC: [MessageHandler(filters.TEXT & ~filters.COMMAND, altura_imc)],
            PESO_TMB: [MessageHandler(filters.TEXT & ~filters.COMMAND, peso_tmb)],
            ALTURA_TMB: [MessageHandler(filters.TEXT & ~filters.COMMAND, altura_tmb)],
            IDADE_TMB: [MessageHandler(filters.TEXT & ~filters.COMMAND, idade_tmb)],
            SEXO_TMB: [CallbackQueryHandler(sexo_tmb)],
            NIVEL_ATIVIDADE_TMB: [CallbackQueryHandler(nivel_atividade_tmb)],
            PESO_FAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, peso_fat)],
            IDADE_FAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, idade_fat)],
            SEXO_FAT: [CallbackQueryHandler(sexo_fat)]
        },
        fallbacks=[CommandHandler('cancelar', cancel)]
    )

    # Conversa para lembretes
    reminder_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            reminder_type, pattern='^(meal_reminder|water_reminder)$')],
        states={
            LEMBRETE_TIPO: [CallbackQueryHandler(reminder_type)],
            LEMBRETE_HORARIO: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, reminder_time)]
        },
        fallbacks=[CommandHandler('cancelar', cancel)]
    )

    # Adicionar manipuladores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(meal_conv)
    application.add_handler(goal_conv)
    application.add_handler(water_conv)
    application.add_handler(calc_conv)
    application.add_handler(reminder_conv)
    application.add_handler(CallbackQueryHandler(button))
    application.add_error_handler(error_handler)

    # Configurar lembretes salvos
    await setup_reminders(application)

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

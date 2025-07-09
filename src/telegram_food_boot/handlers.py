import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from config import food_data
from database import save_meal, save_calculation, save_reminder, get_daily_summary
from utils import translations, get_food_nutrients, calculate_imc, calculate_tmb, calculate_tdee, calculate_fat_percentage

# Configurar logging
logger = logging.getLogger(__name__)

# Estados da conversa
TIPO_REFEICAO, SELECAO_ALIMENTO, QUANTIDADE, CONFIRMAR = range(4)
TIPO_META, VALOR_META = range(2, 4)
QUANTIDADE_AGUA = 0
CALCULADORA, PESO_IMC, ALTURA_IMC, PESO_TMB, ALTURA_TMB, IDADE_TMB, SEXO_TMB, NIVEL_ATIVIDADE_TMB, PESO_FAT, IDADE_FAT, SEXO_FAT = range(
    7, 18)
LEMBRETE_TIPO, LEMBRETE_HORARIO = range(18, 20)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o bot e exibe o menu principal."""
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
        await save_meal(user_id, context.user_data['meal_type'], context.user_data['food_id'], context.user_data['quantity'])
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
        await update.message.reply_text(translations['pt']['select_gender_tmb'], reply_markup=reply_markup)
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
    imc, _, _ = calculate_imc(
        context.user_data['weight'], context.user_data.get('height', 170))
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
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        user_id = update.message.from_user.id
        reminder_type = context.user_data['reminder_type']
        await save_reminder(user_id, reminder_type, time_str)

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

# Definir manipuladores
start = CommandHandler("start", start)
button = CallbackQueryHandler(button)
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
        CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)]
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)
goal_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(goal_type, pattern='^goal_')],
    states={
        TIPO_META: [CallbackQueryHandler(goal_type)],
        VALOR_META: [MessageHandler(
            filters.TEXT & ~filters.COMMAND, goal_value)]
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)
water_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(button, pattern='^track_water$')],
    states={
        QUANTIDADE_AGUA: [MessageHandler(
            filters.TEXT & ~filters.COMMAND, track_water)]
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)
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

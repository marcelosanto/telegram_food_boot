from datetime import datetime

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


def get_food_nutrients(food_id, quantity, food_data):
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

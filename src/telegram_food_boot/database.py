from telegram.ext import ContextTypes
from .utils import translations, get_food_nutrients
from .config import food_data
from datetime import datetime, timedelta
import aiosqlite
from contextlib import asynccontextmanager


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
        await db.execute('''CREATE TABLE IF NOT EXISTS users
                                 (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS user_tokens
                                 (user_id INTEGER PRIMARY KEY, access_token TEXT NOT NULL,
                                  FOREIGN KEY (user_id) REFERENCES users (user_id))''')
        await db.commit()


@asynccontextmanager
async def get_db_connection():
    """Retorna uma conexão assíncrona com o banco de dados."""
    db = await aiosqlite.connect('nutribot.db')
    try:
        yield db
    finally:
        await db.close()


async def save_meal(user_id, meal_type, food_id, quantity, db):
    """Salva uma refeição no banco de dados."""
    async with db.execute('INSERT INTO meals (user_id, meal_type, food_id, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
                          (user_id, meal_type, food_id, quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))):
        await db.commit()


async def save_calculation(user_id, calc_type, result, details, db):
    """Salva um cálculo (IMC, TMB, TDEE, Fat) no banco de dados."""
    async with db.execute('INSERT INTO calculations (user_id, type, result, details, timestamp) VALUES (?, ?, ?, ?, ?)',
                          (user_id, calc_type, result, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))):
        await db.commit()


async def save_reminder(user_id, reminder_type, time, db):
    """Salva um lembrete no banco de dados."""
    async with db.execute('INSERT OR REPLACE INTO reminders (user_id, type, time) VALUES (?, ?, ?)',
                          (user_id, reminder_type, time)):
        await db.commit()


async def get_daily_summary(user_id, date, db):
    """Gera um resumo nutricional diário detalhado."""
    summary = {'meals': {}, 'goals': {}, 'water': 0, 'calculations': []}
    summary['text'] = translations['pt']['daily_summary'].format(
        date=date)

    # Resumo das refeições
    total = {'energy_kcal': 0, 'protein_g': 0,
             'lipid_g': 0, 'carbohydrate_g': 0, 'fiber_g': 0}
    async with db.execute('SELECT meal_type, food_id, quantity, timestamp FROM meals WHERE user_id = ? AND date(timestamp) = ?',
                          (user_id, date)) as cursor:
        meals = await cursor.fetchall()
        if meals:
            summary['text'] += translations['pt']['meals_summary']
            for meal_type, food_id, quantity, timestamp in meals:
                nutrients = get_food_nutrients(food_id, quantity)
                if nutrients:
                    summary['meals'][timestamp] = {
                        'meal_type': meal_type,
                        'description': nutrients['description'],
                        'quantity': quantity,
                        'nutrients': {k: v for k, v in nutrients.items() if k in total}
                    }
                    summary['text'] += f"• *{meal_type.capitalize()}* às {timestamp.split(' ')[1]}: {nutrients['description']} ({quantity}g)\n"
                    summary['text'] += f"  Calorias: {nutrients['energy_kcal']:.1f} kcal, Proteínas: {nutrients['protein_g']:.1f}g, Carboidratos: {nutrients['carbohydrate_g']:.1f}g, Lipídios: {nutrients['lipid_g']:.1f}g, Fibras: {nutrients['fiber_g']:.1f}g\n"
                    for key in total:
                        total[key] += nutrients[key]
            summary['text'] += "\n*Totais do Dia*\n"
            for key, value in total.items():
                summary['text'] += f"• {key.replace('_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')}: *{value:.1f}*\n"
        else:
            summary['text'] += translations['pt']['no_meals'] + "\n"

    # Progresso das metas
    async with db.execute('SELECT nutrient, value FROM goals WHERE user_id = ?', (user_id,)) as cursor:
        goals = await cursor.fetchall()
        if goals:
            summary['text'] += translations['pt']['goals_progress']
            for nutrient, goal in goals:
                current = total.get(nutrient, 0)
                percentage = (current / goal * 100) if goal > 0 else 0
                summary['goals'][nutrient] = {
                    'current': current, 'goal': goal, 'percentage': percentage}
                summary['text'] += f"• {nutrient.replace('_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')}: *{current:.1f}/{goal:.1f}* ({percentage:.1f}%)\n"

    # Consumo de água
    async with db.execute('SELECT SUM(amount) FROM water WHERE user_id = ? AND date = ?',
                          (user_id, date)) as cursor:
        total_water = (await cursor.fetchone())[0] or 0
        summary['water'] = total_water
        summary['text'] += translations['pt']['water_summary']
        summary['text'] += f"• Total: *{total_water:.0f}ml*\n"

    # Últimos cálculos
    async with db.execute('SELECT type, result, details FROM calculations WHERE user_id = ? ORDER BY timestamp DESC LIMIT 2',
                          (user_id,)) as cursor:
        calculations = await cursor.fetchall()
        if calculations:
            summary['text'] += translations['pt']['calculations_summary']
            for calc_type, result, details in calculations:
                summary['calculations'].append(
                    {'type': calc_type, 'result': result, 'details': details})
                summary['text'] += f"• {calc_type}: *{result:.1f}* ({details})\n"

    return summary


async def create_user(username: str, password_hash: str):
    """Cria um novo usuário no banco de dados."""
    async with aiosqlite.connect('nutribot.db') as db:
        try:
            cursor = await db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
            await db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            return None  # Username already exists


async def get_user_by_username(username: str):
    """Recupera um usuário pelo nome de usuário."""
    async with aiosqlite.connect('nutribot.db') as db:
        cursor = await db.execute('SELECT user_id, username, password_hash FROM users WHERE username = ?', (username,))
        return await cursor.fetchone()


async def setup_reminders(application):
    """Configura lembretes salvos no banco de dados ao iniciar o bot."""
    async with aiosqlite.connect('nutribot.db') as db:
        cursor = await db.execute('SELECT user_id, type, time FROM reminders')
        reminders = await cursor.fetchall()

        job_queue = application.job_queue
        for user_id, reminder_type, time_str in reminders:
            async def send_reminder(context: ContextTypes):
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

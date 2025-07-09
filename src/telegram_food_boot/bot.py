import json
import logging
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
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load food data from JSON
with open('tabela_alimentos.json', 'r', encoding='utf-8') as f:
    food_data = json.load(f)

# In-memory user data (replace with database for production)
user_data = {}

# Conversation states
MEAL_TYPE, FOOD_SELECTION, QUANTITY, CONFIRM = range(4)
GOAL_TYPE, GOAL_VALUE = range(2, 4)
WATER_AMOUNT = 0

# Helper functions


def get_food_nutrients(food_id, quantity):
    """Calculate nutrients for a given food and quantity."""
    for food in food_data:
        if food['id'] == food_id:
            factor = quantity / 100  # Adjust for quantity in grams
            return {
                'description': food['description'],
                'energy_kcal': float(food['energy_kcal']) * factor if food['energy_kcal'] != 'NA' else 0,
                'protein_g': float(food['protein_g']) * factor if food['protein_g'] != 'NA' else 0,
                'lipid_g': float(food['lipid_g']) * factor if food['lipid_g'] != 'NA' else 0,
                'carbohydrate_g': float(food['carbohydrate_g']) * factor if food['carbohydrate_g'] != 'NA' else 0,
                'fiber_g': float(food['fiber_g']) * factor if food['fiber_g'] != 'NA' else 0
            }
    return None


def save_meal(user_id, meal_type, food_id, quantity):
    """Save meal data for a user."""
    if user_id not in user_data:
        user_data[user_id] = {'meals': [], 'goals': {}, 'water': 0}
    nutrients = get_food_nutrients(food_id, quantity)
    if nutrients:
        user_data[user_id]['meals'].append({
            'meal_type': meal_type,
            'food': nutrients,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })


def get_daily_summary(user_id):
    """Generate a daily nutritional summary."""
    if user_id not in user_data or not user_data[user_id]['meals']:
        return "No meals registered today."

    total = {'energy_kcal': 0, 'protein_g': 0,
             'lipid_g': 0, 'carbohydrate_g': 0, 'fiber_g': 0}
    summary = f"Daily Summary ({datetime.now().strftime('%Y-%m-%d')}):\n"

    for meal in user_data[user_id]['meals']:
        today = datetime.now().strftime('%Y-%m-%d')
        meal_date = meal['timestamp'].split()[0]
        if meal_date == today:
            for key in total:
                total[key] += meal['food'][key]

    for key, value in total.items():
        summary += f"{key.replace('_g', ' (g)').replace('energy_kcal', 'Calories (kcal)')}: {value:.1f}\n"

    if 'goals' in user_data[user_id]:
        summary += "\nGoals Progress:\n"
        for nutrient, goal in user_data[user_id]['goals'].items():
            current = total.get(nutrient, 0)
            summary += f"{nutrient.replace('_g', ' (g)').replace('energy_kcal', 'Calories (kcal)')}: {current:.1f}/{goal:.1f}\n"

    return summary

# Bot commands


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the bot and show main menu."""
    keyboard = [
        [InlineKeyboardButton("Register Meal", callback_data='register_meal')],
        [InlineKeyboardButton("View Summary", callback_data='summary')],
        [InlineKeyboardButton("Set Goals", callback_data='set_goals')],
        [InlineKeyboardButton("Track Water", callback_data='track_water')],
        [InlineKeyboardButton("Healthy Tips", callback_data='tips')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to NutriBot! Choose an option:", reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()

    if query.data == 'register_meal':
        keyboard = [
            [InlineKeyboardButton("Breakfast", callback_data='breakfast')],
            [InlineKeyboardButton("Lunch", callback_data='lunch')],
            [InlineKeyboardButton(
                "Afternoon Snack", callback_data='afternoon_snack')],
            [InlineKeyboardButton("Dinner", callback_data='dinner')],
            [InlineKeyboardButton("Supper", callback_data='supper')],
            [InlineKeyboardButton("Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select meal type:", reply_markup=reply_markup)
        return MEAL_TYPE
    elif query.data == 'summary':
        summary = get_daily_summary(query.from_user.id)
        await query.message.reply_text(summary)
    elif query.data == 'set_goals':
        keyboard = [
            [InlineKeyboardButton(
                "Calories", callback_data='goal_energy_kcal')],
            [InlineKeyboardButton("Protein", callback_data='goal_protein_g')],
            [InlineKeyboardButton(
                "Carbohydrates", callback_data='goal_carbohydrate_g')],
            [InlineKeyboardButton("Lipids", callback_data='goal_lipid_g')],
            [InlineKeyboardButton("Fiber", callback_data='goal_fiber_g')],
            [InlineKeyboardButton("Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select nutrient to set goal:", reply_markup=reply_markup)
        return GOAL_TYPE
    elif query.data == 'track_water':
        await query.message.reply_text("Enter water intake (ml):")
        return WATER_AMOUNT
    elif query.data == 'tips':
        tips = [
            "Include whole grains like oats for more fiber!",
            "Nuts like almonds are great for healthy fats.",
            "Stay hydrated: aim for 2L of water daily.",
            "Try adding soybeans for plant-based protein."
        ]
        await query.message.reply_text(tips[datetime.now().day % len(tips)])
    elif query.data == 'cancel':
        await query.message.reply_text("Action cancelled.")
        return ConversationHandler.END

# Meal registration conversation


async def meal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text("Meal registration cancelled.")
        return ConversationHandler.END

    context.user_data['meal_type'] = query.data
    keyboard = [
        [InlineKeyboardButton(food['description'],
                              callback_data=str(food['id']))]
        for food in food_data[:5]  # Show first 5 foods for simplicity
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data='cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Select a food:", reply_markup=reply_markup)
    return FOOD_SELECTION


async def food_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text("Meal registration cancelled.")
        return ConversationHandler.END

    context.user_data['food_id'] = int(query.data)
    await query.message.reply_text("Enter quantity (grams):")
    return QUANTITY


async def quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = float(update.message.text)
        if quantity <= 0:
            await update.message.reply_text("Please enter a positive number.")
            return QUANTITY
        context.user_data['quantity'] = quantity
        food = next(
            f for f in food_data if f['id'] == context.user_data['food_id'])
        await update.message.reply_text(
            f"Confirm: {quantity}g of {food['description']} for {context.user_data['meal_type']}?\n"
            f"Reply 'yes' or 'no'."
        )
        return CONFIRM
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return QUANTITY


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = update.message.text.lower()
    if response == 'yes':
        save_meal(
            update.message.from_user.id,
            context.user_data['meal_type'],
            context.user_data['food_id'],
            context.user_data['quantity']
        )
        await update.message.reply_text("Meal registered successfully!")
    else:
        await update.message.reply_text("Meal registration cancelled.")
    return ConversationHandler.END

# Goal setting conversation


async def goal_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text("Goal setting cancelled.")
        return ConversationHandler.END

    context.user_data['goal_type'] = query.data.replace('goal_', '')
    await query.message.reply_text(f"Enter goal for {context.user_data['goal_type'].replace('_g', ' (g)').replace('energy_kcal', 'Calories (kcal)')}:")
    return GOAL_VALUE


async def goal_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text)
        if value <= 0:
            await update.message.reply_text("Please enter a positive number.")
            return GOAL_VALUE
        user_id = update.message.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {'meals': [], 'goals': {}, 'water': 0}
        user_data[user_id]['goals'][context.user_data['goal_type']] = value
        await update.message.reply_text(f"Goal for {context.user_data['goal_type'].replace('_g', ' (g)').replace('energy_kcal', 'Calories (kcal)')} set to {value}.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return GOAL_VALUE

# Water tracking


async def track_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Please enter a positive number.")
            return WATER_AMOUNT
        user_id = update.message.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {'meals': [], 'goals': {}, 'water': 0}
        user_data[user_id]['water'] += amount
        await update.message.reply_text(f"Added {amount}ml of water. Total today: {user_data[user_id]['water']}ml")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return WATER_AMOUNT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Action cancelled.")
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    application = Application.builder().token(
        "7710013199:AAEAQajtgaxRkNJVCy1PvXCq9HR2BJzwpto").build()

    # Conversation handler for meal registration
    meal_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            meal_type, pattern='^(breakfast|lunch|afternoon_snack|dinner|supper)$')],
        states={
            MEAL_TYPE: [CallbackQueryHandler(meal_type)],
            FOOD_SELECTION: [CallbackQueryHandler(food_selection)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Conversation handler for goal setting
    goal_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(goal_type, pattern='^goal_')],
        states={
            GOAL_TYPE: [CallbackQueryHandler(goal_type)],
            GOAL_VALUE: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, goal_value)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Conversation handler for water tracking
    water_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern='^track_water$')],
        states={
            WATER_AMOUNT: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, track_water)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(meal_conv)
    application.add_handler(goal_conv)
    application.add_handler(water_conv)
    application.add_handler(CallbackQueryHandler(button))
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling()


if __name__ == '__main__':
    main()

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional
from .auth import decode_token  # Import only what's needed
from ..database import save_meal, get_daily_summary, save_calculation, save_reminder, create_user, get_user_by_username
from ..utils import translations, get_food_nutrients, calculate_imc, calculate_tmb, calculate_tdee, calculate_fat_percentage
from ..config import food_data, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from .models import MealCreate, GoalCreate, WaterCreate, CalculationCreate, ReminderCreate, SummaryResponse, TipResponse, UserCreate, UserLogin, Token
from .dependencies import get_db, get_user_id, verify_password, get_password_hash

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


@router.post("/meals")
async def create_meal(meal: MealCreate, db: aiosqlite.Connection = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    user_id = await get_user_id_from_username(payload.get("sub"), db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    await db.execute(
        "INSERT INTO meals (user_id, meal_type, food_id, quantity, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, meal.meal_type, meal.food_id, meal.quantity, datetime.utcnow())
    )
    await db.commit()
    return {"message": "Meal recorded successfully"}


@router.get("/summary/{user_id}")
async def get_summary(user_id: int, token: str = Depends(oauth2_scheme), db: aiosqlite.Connection = Depends(get_db)):
    payload = decode_token(token)
    username = payload.get("sub")
    db_user_id = await get_user_id_from_username(username, db)
    if db_user_id != user_id:
        raise HTTPException(
            status_code=401, detail="Invalid user ID for this token")
    query = await db.execute("SELECT SUM(amount) FROM water WHERE user_id = ?", (user_id,))
    total_water = (await query.fetchone())[0] or 0
    return {"text": f"Summary for user {user_id}: Total water consumed: {total_water}ml (placeholder)"}


@router.post("/goals")
async def create_goal(goal: GoalCreate, user_id: int = Depends(get_user_id), db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute('INSERT OR REPLACE INTO goals (user_id, nutrient, value) VALUES (?, ?, ?)',
                          (user_id, goal.nutrient, goal.value)) as cursor:
        await db.commit()
    nutrient_display = goal.nutrient.replace(
        '_g', ' (g)').replace('energy_kcal', 'Calorias (kcal)')
    return {"message": translations['pt']['goal_set'].format(nutrient=nutrient_display, value=goal.value)}


@router.post("/water")
async def register_water(amount: float, token: str = Depends(oauth2_scheme), db: aiosqlite.Connection = Depends(get_db)):
    payload = decode_token(token)
    username = payload.get("sub")
    user_id = await get_user_id_from_username(username, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    await db.execute(
        "INSERT INTO water (user_id, amount, date) VALUES (?, ?, ?)",
        (user_id, amount, datetime.utcnow().isoformat())
    )
    await db.commit()
    return {"message": "Water registered"}


@router.get("/tips", response_model=TipResponse)
async def get_tip():
    tips = [
        "🌾 Inclua grãos integrais como aveia para mais fibras!",
        "🥜 Nozes como amêndoas são ótimas para gorduras saudáveis.",
        "💧 Mantenha-se hidratado: busque 2L de água por dia.",
        "🌱 Experimente adicionar soja para proteína vegetal."
    ]
    return TipResponse(tip=tips[datetime.now().day % len(tips)])


@router.post("/calculations")
async def perform_calculation(calc: CalculationCreate, user_id: int = Depends(get_user_id), db: aiosqlite.Connection = Depends(get_db)):
    if calc.calc_type == "imc":
        if not calc.height:
            raise HTTPException(
                status_code=400, detail="Altura é obrigatória para IMC")
        imc, category, interpretation = calculate_imc(calc.weight, calc.height)
        await save_calculation(user_id, "IMC", imc, f"Peso: {calc.weight}kg, Altura: {calc.height}cm, Categoria: {category}", db)
        return {"message": translations['pt']['imc_result'].format(imc=imc, category=category, interpretation=interpretation)}
    elif calc.calc_type in ["tmb", "tdee"]:
        if not all([calc.height, calc.age, calc.gender]):
            raise HTTPException(
                status_code=400, detail="Altura, idade e sexo são obrigatórios para TMB/TDEE")
        tmb = calculate_tmb(calc.weight, calc.height, calc.age, calc.gender)
        if calc.calc_type == "tmb":
            await save_calculation(user_id, "TMB", tmb, f"Peso: {calc.weight}kg, Altura: {calc.height}cm, Idade: {calc.age} anos, Sexo: {calc.gender}", db)
            return {"message": translations['pt']['tmb_result'].format(tmb=tmb)}
        else:  # tdee
            if not calc.activity_level:
                raise HTTPException(
                    status_code=400, detail="Nível de atividade é obrigatório para TDEE")
            tdee = calculate_tdee(tmb, calc.activity_level)
            activity_labels = {
                'sedentary': 'Sedentário (pouco ou nenhum exercício)',
                'light': 'Leve (exercício leve 1-3 dias/semana)',
                'moderate': 'Moderado (exercício moderado 3-5 dias/semana)',
                'active': 'Ativo (exercício intenso 6-7 dias/semana)',
                'very_active': 'Muito Ativo (exercício muito intenso ou trabalho físico)'
            }
            await save_calculation(user_id, "TDEE", tdee, f"Peso: {calc.weight}kg, Altura: {calc.height}cm, Idade: {calc.age} anos, Sexo: {calc.gender}, Nível de Atividade: {activity_labels[calc.activity_level]}", db)
            return {"message": translations['pt']['tdee_result'].format(tdee=tdee, activity_level=activity_labels[calc.activity_level])}
    elif calc.calc_type == "fat":
        if not all([calc.age, calc.gender]):
            raise HTTPException(
                status_code=400, detail="Idade e sexo são obrigatórios para percentual de gordura")
        height = calc.height or 170  # Valor padrão se altura não fornecida
        imc, _, _ = calculate_imc(calc.weight, height)
        fat = calculate_fat_percentage(imc, calc.age, calc.gender)
        await save_calculation(user_id, "Fat Percentage", fat, f"Peso: {calc.weight}kg, Idade: {calc.age} anos, Sexo: {calc.gender}", db)
        return {"message": translations['pt']['fat_percentage_result'].format(fat=fat)}
    else:
        raise HTTPException(status_code=400, detail="Tipo de cálculo inválido")


@router.post("/reminders")
async def create_reminder(reminder: ReminderCreate, user_id: int = Depends(get_user_id), db: aiosqlite.Connection = Depends(get_db)):
    try:
        hours, minutes = map(int, reminder.time.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        await save_reminder(user_id, reminder.type, reminder.time, db)
        return {
            "message": translations['pt']['reminder_set'].format(
                type='Refeição' if reminder.type == 'meal_reminder' else 'Água',
                time=reminder.time
            )
        }
    except ValueError:
        raise HTTPException(
            status_code=400, detail=translations['pt']['invalid_time'])


@router.post("/users")
async def create_user(form_data: OAuth2PasswordRequestForm = Depends(), db: aiosqlite.Connection = Depends(get_db)):
    hashed_password = get_password_hash(form_data.password)
    try:
        await db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (form_data.username, hashed_password)
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    access_token = create_access_token(form_data.username)
    return {"access_token": access_token, "token_type": "bearer"}


def create_access_token(data: str, expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": data}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: aiosqlite.Connection = Depends(get_db)):
    query = await db.execute("SELECT username, password_hash FROM users WHERE username = ?", (form_data.username,))
    user = await query.fetchone()
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(form_data.username)
    return {"access_token": access_token, "token_type": "bearer"}

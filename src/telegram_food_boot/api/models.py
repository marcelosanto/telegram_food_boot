from pydantic import BaseModel
from typing import Optional


class MealCreate(BaseModel):
    user_id: int
    meal_type: str
    food_id: int
    quantity: float


class GoalCreate(BaseModel):
    user_id: int
    nutrient: str
    value: float


class WaterCreate(BaseModel):
    user_id: int
    amount: float


class CalculationCreate(BaseModel):
    user_id: int
    calc_type: str
    weight: float
    height: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None


class ReminderCreate(BaseModel):
    user_id: int
    type: str
    time: str


class SummaryResponse(BaseModel):
    user_id: int
    date: str
    meals: dict
    goals: dict
    water: float
    calculations: list


class TipResponse(BaseModel):
    tip: str


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

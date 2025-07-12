from fastapi import FastAPI
from .routes import router
from ..database import init_db

app = FastAPI(
    title="NutriBot API",
    description="API para rastreamento de refeições, água, metas e cálculos nutricionais"
)
app.include_router(router, prefix="/api/v1")

# Inicializar banco de dados ao iniciar


@app.on_event("startup")
async def startup_event():
    await init_db()

    # Incluir rotas
    app.include_router(router)

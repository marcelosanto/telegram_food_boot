from webhook import webhook_handler
from handlers import (
    start,
    meal_conv,
    goal_conv,
    water_conv,
    calc_conv,
    reminder_conv,
    button,
    error_handler,
)
from database import init_db, setup_reminders
from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT
from aiohttp import web
from telegram.ext import Application
import logging
import asyncio


# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


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

    # Adicionar manipuladores
    application.add_handler(start)
    application.add_handler(meal_conv)
    application.add_handler(goal_conv)
    application.add_handler(water_conv)
    application.add_handler(calc_conv)
    application.add_handler(reminder_conv)
    application.add_handler(button)
    # Corrigido para add_error_handler
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

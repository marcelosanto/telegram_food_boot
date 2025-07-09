import logging
from telegram import Update
from aiohttp import web

logger = logging.getLogger(__name__)


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

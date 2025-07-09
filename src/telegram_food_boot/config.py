import json
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))

# Carregar dados de alimentos do JSON
with open('tabela_alimentos.json', 'r', encoding='utf-8') as f:
    food_data = json.load(f)

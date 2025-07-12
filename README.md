
# NutriBot - Telegram Food Boot

Um bot do Telegram e uma aplicação FastAPI para rastreamento de refeições, consumo de água, metas nutricionais e cálculos de saúde, com autenticação de usuários.

## Estrutura do Projeto

```
telegram_food_boot/
├── src/
│   └── telegram_food_boot/
│       ├── api/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   ├── main.py
│       │   ├── models.py
│       │   ├── routes.py
│       ├── __init__.py
│       ├── bot.py
│       ├── config.py
│       ├── database.py
│       ├── handlers.py
│       ├── utils.py
│       ├── webhook.py
├── tabela_alimentos.json
├── .env
├── poetry.lock
├── pyproject.toml
├── nutribot.db
├── README.md

```

## Funcionalidades

-   **Bot do Telegram**: Permite registrar refeições, definir metas nutricionais, rastrear consumo de água, visualizar resumos diários, configurar lembretes e realizar cálculos (IMC, TMB, TDEE, percentual de gordura).
-   **FastAPI**: Fornece endpoints RESTful para rastreamento de refeições, metas, água, cálculos, lembretes e autenticação de usuários.
-   **Banco de Dados**: SQLite (`nutribot.db`) armazena refeições, metas, consumo de água, cálculos, lembretes e credenciais de usuários.
-   **Autenticação**: Login baseado em JWT e criação de usuários para acesso seguro à API.

## Pré-requisitos

-   Python 3.13+
-   [Poetry](https://python-poetry.org/) para gerenciamento de dependências
-   [ngrok](https://ngrok.com/) para expor o bot e a API externamente (opcional)
-   Um token de bot do Telegram obtido via [BotFather](https://t.me/BotFather)

## Configuração

1.  **Clonar o Repositório**:
    
    ```bash
    git clone https://github.com/marcelosanto/telegram_food_boot.git
    cd telegram_food_boot
    
    ```
    
2.  **Instalar Dependências**:
    
    ```bash
    poetry install
    
    ```
    
3.  **Configurar Variáveis de Ambiente**:  
    Crie um arquivo `.env` na raiz do projeto:
    
    ```bash
    echo "BOT_TOKEN=seu_token_de_bot_aqui" >> .env
    echo "WEBHOOK_URL=https://seu-ngrok-id.ngrok-free.app/webhook" >> .env
    echo "WEBHOOK_PORT=8443" >> .env
    echo "API_PORT=8000" >> .env
    
    ```
    
    Substitua `seu_token_de_bot_aqui` pelo token do seu bot e `seu-ngrok-id` pela URL do ngrok (se usar).
    
4.  **Inicializar o Banco de Dados**:
    
    ```bash
    poetry run python -c "from src.telegram_food_boot.database import init_db; import asyncio; asyncio.run(init_db())"
    
    ```
    

## Executando a Aplicação

### Bot do Telegram

Execute o bot em modo pacote:

```bash
poetry run python -m src.telegram_food_boot.bot

```

-   O bot iniciará um servidor webhook em `http://0.0.0.0:8443`.
-   Teste enviando `/start` ao seu bot (ex.: `@ClipedAutomacaiBot`).
-   Para acesso externo, use o ngrok:
    
    ```bash
    ngrok http 8443
    
    ```
    
    Atualize `WEBHOOK_URL` no `.env` com a URL do ngrok.

### FastAPI

Execute a API:

```bash
poetry run uvicorn src.telegram_food_boot.api.main:app --host 0.0.0.0 --port 8000

```

-   Acesse a API em `http://localhost:8000`.
-   Veja a documentação Swagger em `http://localhost:8000/docs`.
-   Para acesso externo, use o ngrok:
    
    ```bash
    ngrok http 8000
    
    ```
    

## Endpoints da API

Todos os endpoints, exceto `/api/v1/users` e `/api/v1/login`, requerem autenticação JWT. Use `/docs` para testes interativos.

-   **POST /api/v1/users**: Cria um novo usuário.
    
    ```bash
    curl -X POST http://localhost:8000/api/v1/users -H "Content-Type: application/json" -d '{"username": "testuser", "password": "testpassword"}'
    
    ```
    
    Retorna um token JWT.
    
-   **POST /api/v1/login**: Autentica um usuário.
    
    ```bash
    curl -X POST http://localhost:8000/api/v1/login -H "Content-Type: application/json" -d '{"username": "testuser", "password": "testpassword"}'
    
    ```
    
    Retorna um token JWT.
    
-   **POST /api/v1/meals**: Registra uma refeição.
    
    ```bash
    curl -X POST http://localhost:8000/api/v1/meals -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"meal_type": "breakfast", "food_id": 1, "quantity": 100}'
    
    ```
    
-   **POST /api/v1/goals**: Define uma meta nutricional.
    
    ```bash
    curl -X POST http://localhost:8000/api/v1/goals -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"nutrient": "energy_kcal", "value": 2000}'
    
    ```
    
-   **POST /api/v1/water**: Registra consumo de água.
    
    ```bash
    curl -X POST http://localhost:8000/api/v1/water -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"amount": 2000}'
    
    ```
    
-   **POST /api/v1/calculations**: Salva um cálculo (IMC, TMB, etc.).
    
    ```bash
    curl -X POST http://localhost:8000/api/v1/calculations -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"type": "IMC", "result": 22.5, "details": "Peso: 70kg, Altura: 1.75m"}'
    
    ```
    
-   **POST /api/v1/reminders**: Configura um lembrete.
    
    ```bash
    curl -X POST http://localhost:8000/api/v1/reminders -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" -d '{"type": "meal_reminder", "time": "12:00"}'
    
    ```
    
-   **GET /api/v1/summary**: Obtém o resumo nutricional diário.
    
    ```bash
    curl -X GET http://localhost:8000/api/v1/summary -H "Authorization: Bearer <access_token>"
    
    ```
    

## Comandos do Bot

-   `/start`: Exibe o menu principal.
-   Interaja via botões inline para rastrear refeições, definir metas, registrar água, ver resumos, cálculos e lembretes.

## Notas de Segurança

-   Substitua o `SECRET_KEY` em `src/telegram_food_boot/api/dependencies.py` por uma chave segura (ex.: `openssl rand -hex 32`).
-   Use HTTPS (via ngrok ou proxy reverso) em produção para proteger requisições da API.

## Solução de Problemas

-   **ModuleNotFoundError**: Certifique-se de que todos os imports em `bot.py`, `handlers.py`, etc., usam imports relativos (ex.: `from .config`).
-   **Erros 404**: Use o prefixo `/api/v1/` nas requisições da API (ex.: `/api/v1/meals`).
-   **Problemas no Banco de Dados**: Verifique permissões do `nutribot.db`:
    
    ```bash
    chmod u+rw nutribot.db
    
    ```
    
-   Verifique logs:
    
    ```bash
    cat *.log
    
    ```
    

## Contribuindo

Envie issues ou pull requests no [repositório GitHub](https://github.com/marcelosanto/telegram_food_boot).

## Autor

-   Marcelo Santos ([@marcelosanto](https://github.com/marcelosanto))

## Licença

MIT License
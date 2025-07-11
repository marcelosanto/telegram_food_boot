
# NutriBot - Telegram Food Boot

NutriBot é um bot do Telegram para rastreamento de refeições, consumo de água, metas nutricionais, cálculos de saúde (IMC, TMB, TDEE, percentual de gordura) e lembretes de refeição e hidratação. Ele utiliza um webhook com `aiohttp` para comunicação com o Telegram e um banco de dados SQLite para armazenamento de dados.

## Funcionalidades

-   **Registrar Refeição**: Registre refeições (café da manhã, almoço, lanche da tarde, jantar, ceia) com alimentos e quantidades, calculando nutrientes (calorias, proteínas, carboidratos, lipídios, fibras).
-   **Ver Resumo**: Visualize um resumo diário de refeições, progresso de metas e consumo de água.
-   **Definir Metas**: Estabeleça metas diárias para calorias, proteínas, carboidratos, lipídios ou fibras.
-   **Rastrear Água**: Registre o consumo diário de água com feedback sobre o total consumido.
-   **Dicas Saudáveis**: Receba dicas diárias sobre alimentação saudável.
-   **Calculadoras**: Calcule IMC, TMB, TDEE e percentual de gordura corporal.
-   **Configurar Lembretes**: Defina lembretes diários para refeições ou hidratação.

## Estrutura do Projeto

```
telegram_food_boot/
├── src/
│   └── telegram_food_boot/
│       ├── __init__.py
│       ├── bot.py          # Configuração do bot e webhook
│       ├── config.py      # Configurações e dados de alimentos
│       ├── database.py    # Funções de banco de dados SQLite
│       ├── handlers.py    # Manipuladores de comandos e conversas
│       ├── utils.py       # Funções utilitárias e traduções
│       └── webhook.py     # Configuração do servidor webhook
├── tabela_alimentos.json  # Dados nutricionais dos alimentos
├── .env                   # Variáveis de ambiente (BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT)
├── .gitignore
├── poetry.lock
├── pyproject.toml
└── README.md

```

## Requisitos

-   Python 3.13+
-   [Poetry](https://python-poetry.org/) para gerenciamento de dependências
-   [ngrok](https://ngrok.com/) para expor o webhook localmente
-   Conta no Telegram e token do bot (obtido via [BotFather](https://t.me/BotFather))

## Instalação

1.  **Clone o repositório**:
    
    ```bash
    git clone https://github.com/marcelosanto/telegram_food_boot.git
    cd telegram_food_boot
    
    ```
    
2.  **Instale as dependências com Poetry**:
    
    ```bash
    poetry install
    
    ```
    
3.  **Configure as variáveis de ambiente**:
    
    -   Crie um arquivo `.env` na raiz do projeto:
        
        ```env
        BOT_TOKEN=seu_token_do_bot
        WEBHOOK_URL=https://seu_ngrok_id.ngrok-free.app/webhook
        WEBHOOK_PORT=8443
        
        ```
        
    -   Substitua `seu_token_do_bot` pelo token fornecido pelo BotFather.
    -   O `WEBHOOK_URL` será atualizado após configurar o ngrok.
4.  **Inicie o ngrok**:
    
    -   Execute:
        
        ```bash
        ngrok http 8443
        
        ```
        
    -   Copie a URL fornecida (ex.: `https://4fe9872.ngrok-free.app`) e atualize o `WEBHOOK_URL` no `.env`.
5.  **Verifique permissões**:
    
    ```bash
    chmod u+rw src/telegram_food_boot/*.py
    chmod u+r .env tabela_alimentos.json
    chmod u+rw nutribot.db
    
    ```
    

## Executando o Bot

1.  **Ative o ambiente virtual do Poetry**:
    
    ```bash
    poetry shell
    
    ```
    
2.  **Inicie o bot**:
    
    ```bash
    python src/telegram_food_boot/bot.py
    
    ```
    
3.  **Verifique o webhook**:
    
    ```bash
    curl https://api.telegram.org/bot<seu_token>/getWebhookInfo
    
    ```
    
    -   Certifique-se de que a URL está correta e `pending_update_count` é 0.
4.  **Teste no Telegram**:
    
    -   Abra o Telegram, busque pelo bot (ex.: `@ClipedAutomacaiBot`) e envie `/start`.
    -   Interaja com as opções do menu:
        -   Registrar Refeição
        -   Ver Resumo
        -   Definir Metas
        -   Rastrear Água
        -   Dicas Saudáveis
        -   Calculadoras
        -   Configurar Lembretes

## Uso

-   **Registrar Refeição**:
    
    -   Clique em "Registrar Refeição", escolha o tipo (ex.: Café da Manhã), selecione um alimento, informe a quantidade (em gramas) e confirme com "sim".
    -   Feedback: "✅ Refeição registrada com sucesso!"
-   **Rastrear Água**:
    
    -   Clique em "Rastrear Água", digite a quantidade (ex.: `2000` para 2000ml).
    -   Feedback: "💦 Adicionado 2000ml de água. Total hoje: _2000ml_"
-   **Definir Metas**:
    
    -   Clique em "Definir Metas", escolha um nutriente (ex.: Calorias), informe o valor (ex.: `2000`).
    -   Feedback: "✅ Meta para Calorias (kcal) definida como 2000"
-   **Ver Resumo**:
    
    -   Clique em "Ver Resumo" para ver refeições, progresso de metas e consumo de água do dia.
-   **Calculadoras**:
    
    -   Escolha uma calculadora (IMC, TMB, TDEE, % de Gordura) e siga as instruções para inserir peso, altura, idade, etc.
-   **Lembretes**:
    
    -   Configure lembretes para refeições ou água, especificando o horário (ex.: `08:00`).

## Depuração

-   **Verificar logs**:
    
    ```bash
    cat *.log
    
    ```
    
    -   Procure por mensagens como:
        
        ```
        Servidor webhook iniciado em http://0.0.0.0:8443
        Webhook configurado para https://seu_ngrok_id.ngrok-free.app/webhook
        
        ```
        
-   **Verificar banco de dados**:
    
    ```bash
    sqlite3 nutribot.db
    .schema
    SELECT * FROM meals WHERE user_id = seu_user_id;
    SELECT * FROM water WHERE user_id = seu_user_id;
    SELECT * FROM goals WHERE user_id = seu_user_id;
    
    ```
    
-   **Resetar webhook** (se necessário):
    
    ```bash
    curl https://api.telegram.org/bot<seu_token>/deleteWebhook
    poetry run python src/telegram_food_boot/bot.py
    
    ```
    

## Dependências Principais

-   `python-telegram-bot`: 22.2.*
-   `aiohttp`: 3.9.*
-   `aiosqlite`: 0.20.*
-   `python-dotenv`: 1.0.*

## Problemas Conhecidos

-   **Avisos PTBUserWarning**: Os `ConversationHandler`s usam `per_message=False`, o que pode não rastrear todas as mensagens em conversas complexas. Isso não afeta o funcionamento atual, mas pode ser ajustado para `per_message=True` se necessário.

## Contribuição

1.  Faça um fork do repositório.
2.  Crie uma branch para sua feature: `git checkout -b minha-feature`.
3.  Commit suas alterações: `git commit -m 'Adiciona minha feature'`.
4.  Push para a branch: `git push origin minha-feature`.
5.  Abra um Pull Request.

## Licença

MIT License

## Contato

Para dúvidas ou suporte, envie uma mensagem no Telegram para `@pacezinho` ou abra uma issue no repositório.
# 🍽️ NutriBot - Telegram Food Boot

Bem-vindo ao **NutriBot**, um bot de Telegram desenvolvido em Python para rastreamento nutricional e promoção de hábitos saudáveis! Este projeto permite que usuários registrem refeições, definam metas nutricionais, monitorem o consumo de água, recebam dicas saudáveis, realizem cálculos de saúde (IMC, TMB, TDEE e percentual de gordura corporal) e configurem lembretes diários. O bot utiliza um banco de dados SQLite para persistência e opera via webhook com `aiohttp` para maior eficiência.

🌟 **Funcionalidades principais**:

-   🍴 **Registro de Refeições**: Registre alimentos consumidos com base em uma tabela nutricional (`tabela_alimentos.json`) e acompanhe nutrientes como calorias, proteínas, carboidratos, lipídios e fibras.
-   📊 **Resumo Diário**: Visualize um resumo detalhado das refeições, progresso de metas, consumo de água e cálculos realizados.
-   🎯 **Metas Nutricionais**: Defina metas diárias para calorias, proteínas, carboidratos, lipídios ou fibras.
-   💧 **Rastreamento de Água**: Registre e monitore o consumo diário de água.
-   🧮 **Calculadoras de Saúde**:
    -   **IMC** (Índice de Massa Corporal): Calcule seu IMC e receba interpretações.
    -   **TMB** (Taxa Metabólica Basal): Estime as calorias queimadas em repouso.
    -   **TDEE** (Gasto Energético Total): Calcule as calorias diárias com base no nível de atividade.
    -   **Percentual de Gordura Corporal**: Estime a gordura corporal usando a fórmula de Deurenberg.
-   ⏰ **Lembretes**: Configure lembretes diários para registrar refeições ou se hidratar.
-   🌱 **Dicas Saudáveis**: Receba dicas diárias para melhorar sua alimentação.

----------

## 🛠️ Pré-requisitos

Para executar o NutriBot, você precisará de:

-   🐍 Python 3.13 ou superior
-   📦 Poetry para gerenciamento de dependências
-   🌐 ngrok para testes locais com webhook
-   📄 Um arquivo `.env` com o token do bot e configurações de webhook
-   🗃️ Arquivo `tabela_alimentos.json` com dados nutricionais

----------

## 📋 Instalação

Siga os passos abaixo para configurar o NutriBot em seu ambiente local.

### 1. Clone o Repositório

```bash
git clone https://github.com/marcelosanto/telegram_food_boot.git
cd telegram_food_boot

```

### 2. Instale o Poetry

Se você ainda não tem o Poetry instalado, instale-o:

```bash
pip install poetry

```

### 3. Instale as Dependências

No diretório do projeto, instale as dependências listadas no `pyproject.toml`:

```bash
poetry install

```

Verifique as versões instaladas:

```bash
poetry show python-telegram-bot aiohttp

```

As dependências principais são:

-   `python-telegram-bot>=22.2,<23.0` (com suporte a webhooks)
-   `aiohttp>=3.9.0`
-   `aiosqlite>=0.20.0`
-   `python-dotenv>=1.0.0`

### 4. Configure o Arquivo `.env`

Crie um arquivo `.env` na raiz do projeto (`/home/marcelo/Projetos/telegram_food_boot/`) com as seguintes variáveis:

```env
BOT_TOKEN=seu_token_do_bot
WEBHOOK_URL=https://seu-ngrok-id.ngrok-free.app/webhook
WEBHOOK_PORT=8443

```

-   **BOT_TOKEN**: Obtenha criando um bot com o [BotFather](https://t.me/BotFather) no Telegram.
-   **WEBHOOK_URL**: URL pública fornecida pelo ngrok (veja o passo 5).
-   **WEBHOOK_PORT**: Porta local para o webhook (padrão: 8443).

Defina permissões adequadas:

```bash
chmod u+r /telegram_food_boot/.env

```

### 5. Configure o ngrok

Para expor o bot localmente ao Telegram, use o ngrok:

```bash
ngrok http 8443

```

Copie a URL fornecida (ex.: `https://abcd1234.ngrok-free.app`) e atualize o `WEBHOOK_URL` no `.env`. Se necessário, configure o token do ngrok:

```bash
ngrok authtoken SEU_TOKEN_NGROK

```

### 6. Verifique o Arquivo de Alimentos

Certifique-se de que o arquivo `tabela_alimentos.json` está na raiz do projeto (`/home/marcelo/Projetos/telegram_food_boot/`). Ele deve conter uma lista de alimentos no formato:

```json
[
  {
    "id": 1,
    "description": "Arroz branco cozido",
    "energy_kcal": "130",
    "protein_g": "2.5",
    "lipid_g": "0.3",
    "carbohydrate_g": "28.2",
    "fiber_g": "0.4"
  },
  ...
]

```

### 7. Execute o Bot

Com o ngrok rodando, inicie o bot:

```bash
poetry run python src/telegram_food_boot/bot.py

```

Ou, dentro do shell do Poetry:

```bash
poetry shell
python src/telegram_food_boot/bot.py

```

O bot configurará o webhook automaticamente e começará a responder no Telegram.

----------

## 🚀 Uso

1.  **Inicie o Bot**:
    
    -   No Telegram, envie `/start` para ver o menu principal com as opções:
        -   🍴 Registrar Refeição
        -   📊 Ver Resumo
        -   🎯 Definir Metas
        -   💧 Rastrear Água
        -   🌱 Dicas Saudáveis
        -   🧮 Calculadoras
        -   ⏰ Configurar Lembretes
2.  **Comandos Disponíveis**:
    
    -   `/start`: Exibe o menu principal.
    -   `/buscar`: Busca alimentos por nome.
    -   `/cancelar`: Cancela a ação atual.
3.  **Exemplos de Interações**:
    
    -   **Registrar Refeição**: Clique em "Registrar Refeição", escolha o tipo (ex.: Café da Manhã), selecione um alimento (ou use `/buscar`), insira a quantidade (ex.: `100`) e confirme com "sim".
    -   **Ver Resumo**: Clique em "Ver Resumo" para ver refeições, metas, água e cálculos do dia.
    -   **Calculadoras**:
        -   **IMC**: Insira peso (ex.: `70`) e altura (ex.: `170`).
        -   **TDEE**: Insira peso, altura, idade, sexo e nível de atividade.
    -   **Lembretes**: Configure lembretes para refeições ou água (ex.: horário `08:00`).

----------

## 📂 Estrutura do Projeto

```plaintext
telegram_food_boot/
├── src/
│   └── telegram_food_boot/
│       └── bot.py              # Código principal do bot
├── tabela_alimentos.json       # Tabela nutricional
├── nutribot.db                 # Banco de dados SQLite (gerado automaticamente)
├── pyproject.toml              # Configuração do Poetry
├── poetry.lock                 # Lockfile do Poetry
├── .env                        # Variáveis de ambiente
└── README.md                   # Este arquivo

```

### Banco de Dados (`nutribot.db`)

O bot usa SQLite para armazenar:

-   **meals**: Refeições registradas (usuário, tipo, alimento, quantidade, data/hora).
-   **goals**: Metas nutricionais (nutriente, valor).
-   **water**: Consumo de água (quantidade, data).
-   **calculations**: Resultados de IMC, TMB, TDEE e percentual de gordura.
-   **reminders**: Lembretes configurados (tipo, horário).

----------

## 🐞 Solução de Problemas

### 1. Botões do Menu Não Aparecem

-   **Verifique**: Logs do script (`cat *.log`) para mensagens como `Enviando menu principal para user_id ... com 7 botões`.
-   **Solução**: Confirme que o `reply_markup` está sendo enviado corretamente em `bot.py`. Teste com:
    
    ```bash
    curl https://api.telegram.org/bot<SEU_TOKEN>/getWebhookInfo
    
    ```
    

### 2. Erro de Dependências

-   **Verifique**: Versões das dependências:
    
    ```bash
    poetry show python-telegram-bot aiohttp
    
    ```
    
-   **Solução**: Reinstale:
    
    ```bash
    poetry add "python-telegram-bot[webhooks]@22.2" aiohttp@3.9.5
    
    ```
    

### 3. ngrok Não Funciona

-   **Verifique**: Porta 8443 está livre:
    
    ```bash
    lsof -i :8443
    
    ```
    
-   **Solução**: Mate processos conflitantes (`kill <pid>`) ou altere `WEBHOOK_PORT` no `.env`.

### 4. Bot Não Responde

-   **Verifique**: Configuração do webhook:
    
    ```bash
    curl https://api.telegram.org/bot<SEU_TOKEN>/getWebhookInfo
    
    ```
    
-   **Solução**: Reinicie o ngrok e o bot, e atualize o `WEBHOOK_URL` no `.env`.

### 5. Erro no Banco de Dados

-   **Verifique**: Permissões do diretório:
    
    ```bash
    chmod -R u+rw /telegram_food_boot
    
    ```
    

----------

## 🌟 Melhorias Futuras

-   📄 **Relatórios**: Adicionar comando `/relatorio` para exportar dados em CSV.
-   🥗 **Filtros de Dieta**: Implementar `/definirdieta` para dietas específicas (ex.: vegana, low-carb).
-   ⏰ **Gerenciamento de Lembretes**: Adicionar opção para desativar lembretes existentes.
-   📱 **Integração com API**: Permitir exportação de dados para outras plataformas.

----------

## 🤝 Contribuição

Contribuições são bem-vindas! Siga os passos abaixo:

1.  Faça um fork do repositório.
2.  Crie uma branch para sua feature:
    
    ```bash
    git checkout -b minha-feature
    
    ```
    
3.  Commit suas alterações:
    
    ```bash
    git commit -m "Adiciona minha feature"
    
    ```
    
4.  Envie para o repositório remoto:
    
    ```bash
    git push origin minha-feature
    
    ```
    
5.  Abra um Pull Request.

----------

## 📜 Licença

Este projeto está licenciado sob a [MIT License](https://grok.com/chat/LICENSE).

----------

## 📞 Contato

Para dúvidas ou sugestões, entre em contato pelo Telegram ou abra uma issue no repositório.

Desenvolvido com 💚 por [Marcelo Santos](https://github.com/marcelosanto).
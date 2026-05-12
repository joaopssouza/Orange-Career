# Orange Career

Este repositorio existe para facilitar o encontro de oportunidades de carreira dentro da empresa onde trabalho. O Orange Career automatiza a coleta de vagas publicadas na plataforma interna, estrutura o conteudo da vaga localmente e envia notificacoes, evitando que oportunidades importantes passem despercebidas.

## O que a aplicacao faz

- Busca vagas por cidade na API de ATS
- Limpa e estrutura a descricao da vaga localmente
- Registra novas vagas em uma planilha do Google Sheets
- Marca vagas encerradas quando elas somem da API em uma execucao posterior
- Envia alertas para um usuario no SeaTalk

## Arquitetura (visao rapida)

- `orange_career/api_client.py`: extracao das vagas na API
- `orange_career/summary_client.py`: estrutura local do resumo da vaga
- `orange_career/sheets_client.py`: persistencia no Google Sheets
- `orange_career/seatalk_webhook_client.py`: notificacao no SeaTalk via webhook
- `orange_career/orchestrator.py`: orquestracao do fluxo
- `main.py`: ponto de entrada

## Requisitos

- Python 3.11+
- Conta de servico do Google Sheets
- SeaTalk via webhook de grupo (conta de sistema)

## Configuracao

Crie um arquivo `.env` local (nao commitar) com base em `.env.example`:

```
GOOGLE_CREDENTIALS=
GOOGLE_SHEET_ID=
SEATALK_WEBHOOK_URL=
SEATALK_WEBHOOK_SIGNATURE=
SEATALK_BOT_NAME=Orange Career
ATS_URL_TEMPLATE=
CITIES=betim,belo horizonte,contagem
```

### Credenciais do Google Sheets

O JSON da conta de serviço deve ficar fora do repositório. Coloque o JSON bruto na variável `GOOGLE_CREDENTIALS` (recomendado) no seu `.env` local e, para execução no GitHub Actions, defina o Secret `GOOGLE_CREDENTIALS` com o conteúdo do JSON.

Para compatibilidade, a aplicação também aceita `GOOGLE_CREDENTIALS_BASE64` (string base64 do JSON). Se você preferir armazenar a credencial como base64, defina o Secret `GOOGLE_CREDENTIALS_BASE64` em vez de `GOOGLE_CREDENTIALS`.

## Instalacao

```
pip install -r requirements.txt
```

## Execucao local

```
python main.py
```

## GitHub Actions

O workflow roda a cada 6 horas e injeta os Secrets com as mesmas chaves do `.env` para ATS, Sheets, Telegram e SeaTalk via webhook.
Veja `.github/workflows/monitor.yml`.

Quando uma vaga some da API e o ciclo termina sem erro de consulta, ela é marcada como `closed` na aba `Vagas` e gera alerta no Telegram/SeaTalk.

### Environment secrets

Crie um Environment chamado `env` em `Settings > Environments` e adicione estes Secrets nele:

- `ATS_URL_TEMPLATE`
- `GOOGLE_CREDENTIALS` (ou `GOOGLE_CREDENTIALS_BASE64` como alternativa)
- `GOOGLE_SHEET_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SEATALK_WEBHOOK_URL`
- `SEATALK_WEBHOOK_SIGNATURE`
- `SEATALK_BOT_NAME`

Os valores não sensíveis, como `CITIES`, continuam podendo ficar no próprio workflow ou no `.env` local.

## Segurança

Nao commite segredos ou arquivos de credenciais. Use `.env` localmente e Secrets no GitHub.

Checklist antes de publicar:

- Confirme que `.env`, arquivos `*.json` de credencial, `auth.bat`, `cookies.json`, `download.json`, `chrome_profile/` e `output/` nao estao sendo versionados.
- Crie os Secrets do GitHub antes de habilitar o workflow.
- Se alguma credencial real apareceu em diff, rotacione essa credencial antes de publicar.

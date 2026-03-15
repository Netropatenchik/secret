# Stas Birthday Quest Bot

Минимальный Telegram-бот с webhook, который:
- по `/start` отправляет приветствие с кнопкой;
- после нажатия кнопки просит ввести ответ;
- принимает только `WIN2026`;
- после правильного ответа отправляет финальное сообщение.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# заполни BOT_TOKEN
uvicorn bot:app --host 0.0.0.0 --port 8080 --reload
```

## Railway

1. Залей файлы в GitHub.
2. Создай новый проект в Railway из GitHub-репозитория.
3. В Variables добавь `BOT_TOKEN`.
4. В Settings → Networking → Public Networking нажми `Generate Domain`.
5. Перезапусти деплой. Railway передаст `RAILWAY_PUBLIC_DOMAIN`, а бот сам установит webhook.
6. Открой бота в Telegram и нажми `/start`.

## Важно

Цвет кнопки задается через Bot API `style: "success"`. Если у пользователя старая версия Telegram, кнопка может отображаться обычной.

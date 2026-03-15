import os
import logging
from typing import Any, Dict, Set

import httpx
from fastapi import FastAPI, HTTPException, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

PORT = int(os.getenv("PORT", "8080"))
SECRET_CODE = os.getenv("SECRET_CODE", "WIN2026")
BIRTHDAY_NAME = os.getenv("BIRTHDAY_NAME", "Стас")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

if not WEBHOOK_BASE_URL and RAILWAY_PUBLIC_DOMAIN:
    WEBHOOK_BASE_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}"

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}" if WEBHOOK_BASE_URL else ""
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

WELCOME_TEXT = (
    f"Привет, {BIRTHDAY_NAME}! Сегодня мы отмечаем твой день рождения и тебя ждет небольшой квест.\n\n"
    "Чтобы получить задание, найди файл в рабочем каталоге, который:\n"
    "• создан сегодня;\n"
    "• имеет расширение .txt;\n"
    "• в названии есть слово task."
)

SUCCESS_TEXT = "Твой подарок в шкафу. Кто ищет, тот найдет! Пуля дура, штык молодец."
PROMPT_TEXT = "Отправь правильный ответ одним сообщением."
WRONG_TEXT = "Неверно. Попробуй еще раз."
IDLE_TEXT = "Нажми кнопку «Ввести правильный ответ», чтобы начать."

# В памяти храним пользователей, которые нажали кнопку и теперь могут вводить ответ.
waiting_for_answer: Set[int] = set()

app = FastAPI(title="Stas Birthday Quest Bot")


async def tg_api(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{TELEGRAM_API}/{method}", json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise HTTPException(status_code=500, detail=f"Telegram API error: {data}")
        return data


async def send_message(chat_id: int, text: str, reply_markup: Dict[str, Any] | None = None) -> None:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    await tg_api("sendMessage", payload)


async def answer_callback(callback_query_id: str, text: str | None = None) -> None:
    payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    await tg_api("answerCallbackQuery", payload)


def success_button() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Ввести правильный ответ",
                    "callback_data": "enter_correct_answer",
                    "style": "success",
                }
            ]
        ]
    }


async def set_webhook() -> None:
    if not WEBHOOK_URL:
        logger.info("WEBHOOK_URL not provided yet. Skipping webhook setup.")
        return
    payload = {
        "url": WEBHOOK_URL,
        "allowed_updates": ["message", "callback_query"],
    }
    result = await tg_api("setWebhook", payload)
    logger.info("Webhook set: %s", result)


@app.on_event("startup")
async def on_startup() -> None:
    await set_webhook()


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ok", "webhook_url": WEBHOOK_URL or "not_set"}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> Dict[str, bool]:
    update = await request.json()

    if "callback_query" in update:
        callback = update["callback_query"]
        callback_id = callback["id"]
        data = callback.get("data", "")
        from_user = callback.get("from", {})
        user_id = from_user.get("id")
        message = callback.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if data == "enter_correct_answer" and user_id and chat_id:
            waiting_for_answer.add(user_id)
            await answer_callback(callback_id)
            await send_message(chat_id, PROMPT_TEXT)
            return {"ok": True}

        await answer_callback(callback_id)
        return {"ok": True}

    if "message" in update:
        message = update["message"]
        text = (message.get("text") or "").strip()
        chat_id = message["chat"]["id"]
        user_id = message.get("from", {}).get("id")

        if text == "/start":
            if user_id:
                waiting_for_answer.discard(user_id)
            await send_message(chat_id, WELCOME_TEXT, reply_markup=success_button())
            return {"ok": True}

        if user_id and user_id in waiting_for_answer:
            if text == SECRET_CODE:
                waiting_for_answer.discard(user_id)
                await send_message(chat_id, SUCCESS_TEXT)
            else:
                await send_message(chat_id, WRONG_TEXT)
            return {"ok": True}

        await send_message(chat_id, IDLE_TEXT)
        return {"ok": True}

    return {"ok": True}

import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import requests
from duckduckgo_search import DDGS
import xml.etree.ElementTree as ET

# Настройка логирования
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([BOT_TOKEN, API_KEY]):
    print("CRITICAL: Missing environment secrets.")
    exit(1)

API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
MODEL_NAME = "qwen/qwen3.8-27b"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для диалога
class AgentStates(StatesGroup):
    waiting_for_task = State()

# --- HARNESS CORE (LLM ENGINE) ---
def call_harness_node(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
    payload = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=50)
    if response.status_code != 200:
        raise RuntimeError(f"Harness Engine Error: {response.text}")
    return response.json()['choices'][0]['message']['content'].strip()

def tool_duckduckgo(query: str) -> list[str]:
    articles = []
    try:
        results = DDGS().text(query, region='ru-ru', max_results=2)
        if results:
            for r in results:
                articles.append(f"Source [Web]: {r.get('title', '')} — {r.get('body', '')}")
    except Exception:
        pass
    return articles

# --- HARNESS PIPELINE ---
def run_interactive_harness(user_task: str) -> str:
    # Node 1: Planner
    search_query = call_harness_node(
        system_prompt="Сформируй один точный поисковый запрос (2-4 слова) на русском языке для этой задачи. Верни ТОЛЬКО запрос без кавычек.",
        user_prompt=user_task,
        temperature=0.2
    )
    
    # Node 2: Retrieval
    raw_data = tool_duckduckgo(search_query)
    context_text = "\n".join(raw_data) if raw_data else "Внешние источники недоступны."

    # Node 3: Synthesis
    draft = call_harness_node(
        system_prompt="Ты инженер-технолог. Напиши качественный технический ответ/пост на основе задачи и контекста.",
        user_prompt=f"Задача: {user_task}\n\nКонтекст:\n{context_text}",
        temperature=0.4
    )

    # Node 4: Critic / Verifier
    final_output = call_harness_node(
        system_prompt="Ты строгий технический редактор. Проверь текст на ошибки, убери воду, сделай формулировки абсолютно профессиональными и точными.",
        user_prompt=f"Отредактируй и верифицируй этот ответ:\n\n{draft}",
        temperature=0.1
    )

    return final_output

# --- TELEGRAM HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я интерактивный инженерный агент с Harness-контуром.\n\n"
        "Напиши мне любую тему или задачу (например: *«Сделай пост про поликарбоксилатные добавки»* или *«Какие нюансы при шлифовке терраццо?»*), "
        "и я пропущу её через агентов поиска и критики."
    )

@dp.message()
async def handle_user_message(message: types.Message):
    user_task = message.text
    processing_msg = await message.answer("🔄 Агент запущен в работу: планирование, поиск, генерация, верификация...")

    try:
        # Запускаем синхронный контур Harness в отдельном потоке, чтобы не вешать бота
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_interactive_harness, user_task)
        
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=processing_msg.message_id,
            text=result,
            parse_mode="Markdown"
        )
    except Exception as e:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=processing_msg.message_id,
            text=f"❌ Ошибка выполнения агента: {e}"
        )

async def main():
    print("Интерактивный бот запущен и слушает сообщения...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

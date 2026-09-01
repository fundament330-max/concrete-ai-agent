import os
import random
import xml.etree.ElementTree as ET
import requests
from duckduckgo_search import DDGS

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API_KEY = os.getenv("DEEPSEEK_API_KEY") # Здесь хранится бесплатный ключ Groq

if not all([BOT_TOKEN, ADMIN_CHAT_ID, API_KEY]):
    print("Ошибка: Отсутствует один из необходимых секретов (BOT_TOKEN, ADMIN_CHAT_ID, DEEPSEEK_API_KEY).")
    exit(1)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
MODEL_NAME = "qwen/qwen3.8-27b"

TOPIC_POOL = [
    "технологии архитектурного бетона и фибробетона",
    "составы смесей и шлифовка покрытий терраццо",
    "автоматизация исполнительной документации и ведение АОСР",
    "контроль качества бетонных смесей и паспорта качества",
    "самоуплотняющийся бетон и современные поликарбоксилатные добавки",
    "гидрофобизаторы и защитные пропитки для бетона"
]

def query_groq(system_prompt: str, user_prompt: str, max_tokens: int = 700) -> str:
    payload = {
        "model": MODEL_NAME,
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    response = requests.post(GROQ_URL, headers=HEADERS, json=payload, timeout=45)
    if response.status_code != 200:
        raise RuntimeError(f"Ошибка Groq API ({response.status_code}): {response.text}")
    return response.json()['choices'][0]['message']['content'].strip()

def search_google_news(query: str) -> list[str]:
    articles = []
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=ru&gl=RU&ceid=RU:ru"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall('./channel/item')[:2]:
                title = item.find('title').text if item.find('title') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else ""
                articles.append(f"Заголовок: {title}\nОписание: {desc}")
    except Exception as e:
        print(f"Ошибка поиска Google News: {e}")
    return articles

def search_duckduckgo(query: str) -> list[str]:
    articles = []
    try:
        results = DDGS().text(query, region='ru-ru', max_results=2)
        if results:
            for r in results:
                articles.append(f"Заголовок: {r.get('title', '')}\nТекст: {r.get('body', '')}")
    except Exception as e:
        print(f"Ошибка DuckDuckGo: {e}")
    return articles

def main():
    base_topic = random.choice(TOPIC_POOL)
    print(f"Базовая тема выпуска: {base_topic}")

    # ЭТАП 1: Формирование точечного поискового запроса
    print("Генерация точечного поискового запроса агентом...")
    try:
        search_query = query_groq(
            system_prompt="Ты поисковый модуль инженерного агента. Сформируй один точный поисковый запрос (2-4 слова) на русском языке для поиска актуальной статьи или норматива по теме. Верни ТОЛЬКО поисковый запрос без кавычек и лишних символов.",
            user_prompt=base_topic,
            max_tokens=40
        )
    except Exception as e:
        print(f"Ошибка генерации запроса, используем базовую тему: {e}")
        search_query = base_topic

    print(f"Поисковый запрос: {search_query}")

    # ЭТАП 2: Сбор данных из сети
    print("Сбор информации из внешних источников...")
    raw_data = search_google_news(search_query) + search_duckduckgo(search_query)
    context_text = "\n\n".join(raw_data) if raw_data else "Актуальные данные не найдены. Используй экспертную инженерную базу."

    # ЭТАП 3: Синтез и форматирование публикации
    print("Синтез публикации через Groq...")
    system_editor = (
        "Ты ведущий инженер-технолог и эксперт по строительным материалам, архитектурному бетону, "
        "терраццо и исполнительной документации. Твоя задача — писать сжатые, строго технические посты "
        "для профессионального Telegram-канала без 'воды' и лишних вводных фраз. "
        "Формат: Заголовок жирным шрифтом, 2 коротких смысловых абзаца с техническими нюансами, "
        "в конце 3-4 профильных хэштега."
    )
    user_editor_prompt = f"Тематика: {base_topic}\n\nСобранные материалы:\n{context_text}\n\nНапиши готовый пост для публикации."

    post_text = query_groq(system_editor, user_editor_prompt, max_tokens=700)

    # Ограничение длины сообщения
    if len(post_text) > 4000:
        post_text = post_text[:4000]

    # ЭТАП 4: Отправка в Telegram
    print("Отправка сообщения в Telegram...")
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    tg_payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": post_text,
        "parse_mode": "Markdown"
    }
    tg_resp = requests.post(tg_url, json=tg_payload, timeout=20)
    
    # Резервная отправка без разметки Markdown при синтаксических конфликтах
    if tg_resp.status_code != 200:
        print("Резервная отправка без Markdown...")
        tg_payload.pop("parse_mode", None)
        tg_resp = requests.post(tg_url, json=tg_payload, timeout=20)

    if tg_resp.status_code == 200:
        print("Пост успешно доставлен в Telegram!")
    else:
        print(f"Ошибка отправки в Telegram: {tg_resp.text}")

if __name__ == "__main__":
    main()

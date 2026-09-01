import os
import random
import xml.etree.ElementTree as ET
import requests
from duckduckgo_search import DDGS

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([BOT_TOKEN, ADMIN_CHAT_ID, API_KEY]):
    print("Ошибка: Отсутствует один из необходимых секретов.")
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
        "temperature": 0.3,
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
    print(f"[Агент] Выбрана тема: {base_topic}")

    # ЭТАП 1: Агент-планировщик генерирует поисковый запрос
    print("[Агент] Шаг 1: Формирование поискового запроса...")
    search_query = query_groq(
        system_prompt="Ты поисковый агент. Сформируй один точный поисковый запрос (2-4 слова) на русском языке. Верни ТОЛЬКО запрос без кавычек.",
        user_prompt=base_topic,
        max_tokens=40
    )
    print(f"[Агент] Запрос: {search_query}")

    # ЭТАП 2: Сбор сырых данных
    print("[Агент] Шаг 2: Сбор контекста из сети...")
    raw_data = search_google_news(search_query) + search_duckduckgo(search_query)
    context_text = "\n\n".join(raw_data) if raw_data else "Используй внутреннюю инженерную базу знаний."

    # ЭТАП 3: Агент-рапитер (Генерация черновика)
    print("[Агент] Шаг 3: Синтез чернового поста...")
    draft_text = query_groq(
        system_prompt=(
            "Ты ведущий инженер-технолог. Напиши черновик поста для Telegram-канала "
            "по строительным технологиям. Структура: Жирный заголовок, 2 емких абзаца фактуры, 3 хэштега."
        ),
        user_prompt=f"Тема: {base_topic}\n\nМатериалы:\n{context_text}",
        max_tokens=600
    )

    # ЭТАП 4: Агент-критик (Валидация и редактура)
    print("[Агент] Шаг 4: Проверка и полировка текста критиком...")
    post_text = query_groq(
        system_prompt=(
            "Ты строгий технический редактор. Проверь текст на наличие рекламной воды, "
            "общих фраз и фактических ошибок. Сделай язык максимально профессиональным, "
            "сухим, инженерным. Убери всю 'лирику'. Верни итоговый вариант поста."
        ),
        user_prompt=f"Отредактируй этот черновик:\n\n{draft_text}",
        max_tokens=600
    )

    if len(post_text) > 4000:
        post_text = post_text[:4000]

    # ЭТАП 5: Публикация
    print("[Агент] Шаг 5: Отправка в Telegram...")
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    tg_payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": post_text,
        "parse_mode": "Markdown"
    }
    tg_resp = requests.post(tg_url, json=tg_payload, timeout=20)
    
    if tg_resp.status_code != 200:
        tg_payload.pop("parse_mode", None)
        tg_resp = requests.post(tg_url, json=tg_payload, timeout=20)

    if tg_resp.status_code == 200:
        print("Пост успешно прошел агентский контур и доставлен!")
    else:
        print(f"Ошибка отправки: {tg_resp.text}")

if __name__ == "__main__":
    main()

import os
import requests
import random
import xml.etree.ElementTree as ET
from duckduckgo_search import DDGS

print("Скрипт запущен! Проверяем ключи...")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([BOT_TOKEN, ADMIN_CHAT_ID, API_KEY]):
    print("Ошибка: Не найден один из ключей!")
    exit(1)

# Темы для поиска в строительной сфере
SEARCH_TOPICS = [
    "архитектурный бетон технологии",
    "покрытия терраццо мозаичный бетон",
    "новые строительные материалы бетон",
    "исполнительная документация строительство АОСР",
    "самоуплотняющийся бетон добавки",
    "гидрофобизаторы пропитки для бетона"
]

def fetch_from_google_rss(topic):
    """Поиск свежих новостей через Google News RSS"""
    print(f"Пробуем поиск через Google News RSS: '{topic}'...")
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(topic)}&hl=ru&gl=RU&ceid=RU:ru"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        root = ET.fromstring(resp.content)
        items = root.findall('./channel/item')
        if items:
            articles = []
            for item in items[:3]:
                title = item.find('title').text if item.find('title') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else ""
                articles.append(f"Заголовок: {title}\nОписание: {desc}")
            return "\n\n".join(articles)
    return None

def fetch_from_ddg(topic):
    """Резервный поиск через DuckDuckGo"""
    print(f"Пробуем поиск через DuckDuckGo: '{topic}'...")
    try:
        results = DDGS().text(topic, region='ru-ru', max_results=3)
        if results:
            return "\n\n".join([f"Заголовок: {r['title']}\nТекст: {r['body']}" for r in results])
    except Exception as e:
        print(f"DuckDuckGo ошибка: {e}")
    return None

# Сбор данных по выбранной теме
selected_topic = random.choice(SEARCH_TOPICS)
print(f"Выбранная тема: {selected_topic}")

collected_data = fetch_from_google_rss(selected_topic)
if not collected_data:
    collected_data = fetch_from_ddg(selected_topic)

if not collected_data:
    print("Внешние источники не ответили, переходим на экспертную генерацию...")
    collected_data = f"Тема выпуска: {selected_topic}. Опиши актуальные технологические требования, нюансы производства или нормативные аспекты."

# Отправка собранного контекста в нейросеть
print("Генерируем пост через Groq...")
url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "model": "qwen/qwen3.8-27b",
    "max_tokens": 700,
    "messages": [
        {
            "role": "system",
            "content": "Ты ведущий инженер и эксперт по архитектурному бетону, терраццо и строительным технологиям. Твоя задача — писать емкие, практические посты для профессионального Telegram-канала на русском языке."
        },
        {
            "role": "user",
            "content": f"Используя следующие исходные материалы:\n\n{collected_data}\n\nНапиши структурированный пост для канала (2-3 абзаца с ключевыми акцентами). В конце добавь 3-4 тематических хэштега."
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    post_text = response.json()['choices'][0]['message']['content']
    print("Текст успешно составлен!")
    
    if len(post_text) > 4000:
        post_text = post_text[:4000]
    
    # Отправка в Telegram
    print("Отправляем в Telegram...")
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    tg_data = {
        "chat_id": ADMIN_CHAT_ID,
        "text": post_text
    }
    tg_resp = requests.post(tg_url, json=tg_data)
    
    if tg_resp.status_code == 200:
        print("Готово! Пост доставлен.")
    else:
        print(f"Ошибка Telegram: {tg_resp.text}")
else:
    print(f"Ошибка нейросети: {response.text}")

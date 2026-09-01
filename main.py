import os
import requests

print("Скрипт запущен! Проверяем ключи...")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Сюда подставится ваш бесплатный ключ от Groq

if not all([BOT_TOKEN, ADMIN_CHAT_ID, API_KEY]):
    print("Ошибка: Не найден один из ключей!")
    exit(1)

print("Ключи на месте. Отправляем запрос к бесплатной нейросети Groq...")

# Запрос к бесплатному API Groq (модель Llama-3.3-70b)
url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {"role": "system", "content": "Ты эксперт по архитектурному бетону, терраццо и строительным технологиям. Пиши емкие, практичные посты для Telegram-канала на русском языке."},
        {"role": "user", "content": "Напиши короткий пост (2 абзаца) про современные добавки для самоуплотняющегося и высокопрочного бетона. Добавь тематические хэштеги."}
    ]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    post_text = response.json()['choices'][0]['message']['content']
    print("Текст от нейросети успешно получен!")
    
    print("Отправляем черновик в Telegram...")
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    tg_data = {
        "chat_id": ADMIN_CHAT_ID,
        "text": post_text
    }
    tg_resp = requests.post(tg_url, json=tg_data)
    
    if tg_resp.status_code == 200:
        print("Готово! Сообщение успешно доставлено в Telegram.")
    else:
        print(f"Ошибка отправки в Telegram: {tg_resp.text}")
else:
    print(f"Ошибка нейросети: {response.text}")

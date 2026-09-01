import os
import requests

print("Скрипт запущен! Проверяем ключи...")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([BOT_TOKEN, ADMIN_CHAT_ID, API_KEY]):
    print("Ошибка: Не найден один из ключей!")
    exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Автоматически получаем список моделей, доступных на вашем ключе
print("Запрашиваем доступные модели Groq...")
models_resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers)

if models_resp.status_code != 200:
    print(f"Ошибка получения моделей: {models_resp.text}")
    exit(1)

available_models = [m["id"] for m in models_resp.json().get("data", [])]
print(f"Доступные модели на аккаунте: {available_models}")

# Выбираем подходящую текстовую модель
chosen_model = None
for m in available_models:
    if "whisper" not in m and "guard" not in m and "vision" not in m:
        chosen_model = m
        break

if not chosen_model and available_models:
    chosen_model = available_models[0]

print(f"Используем модель: {chosen_model}")

# 2. Генерируем пост
url = "https://api.groq.com/openai/v1/chat/completions"
data = {
    "model": chosen_model,
    "messages": [
        {"role": "system", "content": "Ты эксперт по архитектурному бетону, терраццо и строительным технологиям. Пиши емкие, практичные посты для Telegram-канала на русском языке."},
        {"role": "user", "content": "Напиши короткий пост (2 абзаца) про современные добавки для самоуплотняющегося и высокопрочного бетона. Добавь тематические хэштеги."}
    ]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    post_text = response.json()['choices'][0]['message']['content']
    print("Текст от нейросети успешно получен!")
    
    # Защита от превышения лимита Telegram (4096 символов)
    if len(post_text) > 4000:
        print("Текст слишком длинный, обрезаем...")
        post_text = post_text[:4000] + "\n\n[...Текст обрезан из-за лимита Telegram...]"
    
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

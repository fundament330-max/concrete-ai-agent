import os
import requests

print("Скрипт запущен! Проверяем ключи...")

# Загружаем секреты из GitHub Actions
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([BOT_TOKEN, ADMIN_CHAT_ID, DEEPSEEK_API_KEY]):
    print("Ошибка: Не найден один из ключей!")
    exit(1)

print("Ключи на месте. Отправляем запрос к DeepSeek...")

# 1. Запрашиваем текст у нейросети
deepseek_url = "https://api.deepseek.com/chat/completions"
headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "Ты эксперт по архитектурному бетону, терраццо и строительным технологиям. Пиши короткие, емкие посты для Telegram-канала."},
        {"role": "user", "content": "Напиши короткий тестовый пост (2 абзаца) про современные добавки для высокопрочного бетона. Добавь пару хэштегов."}
    ]
}

response = requests.post(deepseek_url, headers=headers, json=data)

if response.status_code == 200:
    post_text = response.json()['choices'][0]['message']['content']
    print("Текст от нейросети успешно получен!")
    
    # 2. Отправляем готовый текст в Telegram
    print("Отправляем черновик в Telegram...")
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    tg_data = {
        "chat_id": ADMIN_CHAT_ID,
        "text": post_text,
        "parse_mode": "Markdown"
    }
    tg_resp = requests.post(tg_url, json=tg_data)
    
    if tg_resp.status_code == 200:
        print("Готово! Сообщение успешно доставлено в Telegram.")
    else:
        print(f"Ошибка отправки в Telegram: {tg_resp.text}")
else:
    print(f"Ошибка от DeepSeek: {response.text}")

import os
import random
import xml.etree.ElementTree as ET
import requests
from duckduckgo_search import DDGS

# --- CONFIGURATION & STATE ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([BOT_TOKEN, ADMIN_CHAT_ID, API_KEY]):
    print("CRITICAL: Missing environment secrets.")
    exit(1)

API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
MODEL_NAME = "qwen/qwen3.8-27b"

TOPIC_POOL = [
    "технологии архитектурного бетона и фибробетона",
    "составы смесей и шлифовка покрытий терраццо",
    "автоматизация исполнительной документации и ведение АОСР",
    "контроль качества бетонных смесей и паспорта качества",
    "самоуплотняющийся бетон и современные поликарбоксилатные добавки",
    "гидрофобизаторы и защитные пропитки для бетона"
]

class AgentState:
    def __init__(self, topic: str):
        self.topic = topic
        self.search_query = ""
        self.raw_context = ""
        self.draft = ""
        self.final_output = ""

# --- LLM ENGINE (HARNESS CORE) ---
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
        raise RuntimeError(f"Harness Engine Error ({response.status_code}): {response.text}")
    return response.json()['choices'][0]['message']['content'].strip()

# --- TOOL NODES ---
def tool_google_news(query: str) -> list[str]:
    articles = []
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=ru&gl=RU&ceid=RU:ru"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall('./channel/item')[:2]:
                title = item.find('title').text if item.find('title') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else ""
                articles.append(f"Source [Google News]: {title} — {desc}")
    except Exception:
        pass
    return articles

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

# --- HARNESS AGENT WORKFLOW ---
def run_harness():
    state = AgentState(topic=random.choice(TOPIC_POOL))
    print(f"[Harness 0/4] Initialized state. Target topic: {state.topic}")

    # Node 1: Planner / Query Generator
    print("[Harness 1/4] Executing Planner Node...")
    state.search_query = call_harness_node(
        system_prompt="Ты модуль планирования поисковых запросов в агенте Harness. Сформируй один точный поисковый запрос (2-4 слова) на русском языке. Верни ТОЛЬКО текст запроса без кавычек.",
        user_prompt=state.topic,
        temperature=0.2
    )
    print(f" -> Query generated: {state.search_query}")

    # Node 2: Tool Execution (Retrieval)
    print("[Harness 2/4] Executing Tool Execution Node (Search)...")
    context_data = tool_google_news(state.search_query) + tool_duckduckgo(state.search_query)
    state.raw_context = "\n".join(context_data) if context_data else "Внешние источники недоступны. Используй внутреннюю фактуру."

    # Node 3: Synthesis / Generator
    print("[Harness 3/4] Executing Synthesis Node...")
    state.draft = call_harness_node(
        system_prompt="Ты инженер-технолог. Напиши черновик технического поста для Telegram-канала. Структура: Жирный заголовок, 2 емких абзаца фактуры с конкретикой, 3 хэштега.",
        user_prompt=f"Тема: {state.topic}\n\nСобранный контекст:\n{state.raw_context}",
        temperature=0.4
    )

    # Node 4: Critic / Verifier Loop
    print("[Harness 4/4] Executing Critic & Verification Node...")
    critic_prompt = (
        "Ты строгий технический редактор и главный технадзор (Harness Verifier). "
        "Проверь черновик на наличие воды, выдуманных фактов и рекламы. "
        "Добейся абсолютной инженерной точности, сухого профессионального тона, "
        "наличия параметров и четкой структуры (жирный заголовок, 2 абзаца, хэштеги). "
        "Выдай окончательный текст."
    )
    state.final_output = call_harness_node(
        system_prompt=critic_prompt,
        user_prompt=f"Проверь и верифицируй этот черновик:\n\n{state.draft}",
        temperature=0.1
    )

    if len(state.final_output) > 4000:
        state.final_output = state.final_output[:4000]

    # Dispatcher / Action Node (Telegram Delivery)
    print("[Harness Dispatch] Sending payload to Telegram...")
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": state.final_output, "parse_mode": "Markdown"}
    resp = requests.post(tg_url, json=payload, timeout=20)
    
    if resp.status_code != 200:
        payload.pop("parse_mode", None)
        resp = requests.post(tg_url, json=payload, timeout=20)

    if resp.status_code == 200:
        print("[Harness Pipeline] Successfully completed and dispatched.")
    else:
        print(f"Dispatcher Error: {resp.text}")

if __name__ == "__main__":
    run_harness()

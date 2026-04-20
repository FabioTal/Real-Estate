import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from groq import Groq
from dotenv import dotenv_values
from database import get_all_listings
from scrapers.merrjep import scrape_merrjep
from notifications.telegram_bot import send_property_notification
import asyncio
import json
import re

config = dotenv_values(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
client = Groq(api_key=config.get("GROQ_API_KEY", ""))

SYSTEM_PROMPT = """
You are a strict Albanian real estate assistant.
Extract EXACTLY what the user asks for. Be very precise.

Extract these details from the user message:
- category: one of [apartamente, shtepi, vila, toke] (default: apartamente)
- location: one of [tirane, durres, vlore, shkoder, all] (default: tirane)
- neighborhood: specific neighborhood mentioned e.g. "astir", "bllok", "don bosko", "fresk", "kodra diellit", "unaza", "paskuqan" etc. Extract EXACTLY what the user says. null if not mentioned.
- max_price: number in EUR if mentioned. If user says "450 euro" or "deri ne 450" set to 450. null if not mentioned.
- min_rooms: room type e.g. "1+1", "2+1", "3+1" if mentioned. null if not mentioned.
- action: one of [search, list, alert, help]
  - search = search now
  - list = show from database
  - alert = set alert
  - help = explain capabilities

Respond ONLY in JSON format, no other text:
{
  "action": "search|list|alert|help",
  "category": "apartamente|shtepi|vila|toke",
  "location": "tirane|durres|vlore|shkoder|all",
  "neighborhood": null or "astir|bllok|fresk|don bosko|...",
  "max_price": null or number,
  "min_rooms": null or "1+1|2+1|3+1",
  "reply": "friendly message in same language as user"
}
"""

conversation_history = []

def parse_user_message(user_message):
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
        max_tokens=500
    )

    reply = response.choices[0].message.content

    conversation_history.append({
        "role": "assistant",
        "content": reply
    })

    try:
        clean = reply.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        parsed = json.loads(clean)
        return parsed
    except:
        return {
            "action": "help",
            "category": "apartamente",
            "location": "tirane",
            "neighborhood": None,
            "max_price": None,
            "min_rooms": None,
            "reply": reply
        }


def extract_price_number(price_str):
    if not price_str:
        return None
    s = price_str.upper().replace(" ", "")
    is_lek = "LEK" in s or "ALL" in s
    s = re.sub(r'[^\d]', '', s)
    if not s:
        return None
    num = int(s)
    if is_lek:
        num = num / 100
    return num


def clean_location(location):
    if not location:
        return "Albania"
    loc = location.strip()
    bad = ["Pallati", "Rruga", "Njësia", "Koordinata", "Vendndodhja",
           "Adresa", "Apliko", "Anulo", "zgjedhur", "Bashkiake"]
    if any(k in loc for k in bad) or len(loc) > 40:
        lower = loc.lower()
        if "tiranë" in lower or "tirane" in lower:
            return "Tiranë"
        elif "durrës" in lower or "durres" in lower:
            return "Durrës"
        elif "vlorë" in lower or "vlore" in lower:
            return "Vlorë"
        elif "shkodër" in lower or "shkoder" in lower:
            return "Shkodër"
        return "Albania"
    return loc


def filter_listings(listings, max_price=None, min_rooms=None, neighborhood=None):
    filtered = []

    for l in listings:
        price_str = (l[4] or "").strip()
        title_str = (l[3] or "").lower()
        loc_str = (l[5] or "").lower()
        desc_str = (l[7] or "").lower()
        url_str = (l[9] or "").lower()

        combined = title_str + " " + loc_str + " " + desc_str + " " + url_str

        if min_rooms:
            if min_rooms.lower() not in combined:
                continue

        if neighborhood:
            neigh_lower = neighborhood.lower().strip()
            if neigh_lower not in combined:
                continue

        if max_price:
            price_num = extract_price_number(price_str)
            if price_num is not None and price_num > max_price:
                continue

        filtered.append(l)

    return filtered


def format_listings_response(listings, max_show=5):
    if not listings:
        return "Nuk u gjetën prona për kriteret tuaja.\nProvoni me kritere më të gjera ose zona të ndryshme."

    response = f"Gjeta {len(listings)} prona që plotësojnë SAKTËSISHT kriteret tuaja!\n\n"
    for l in listings[:max_show]:
        loc = clean_location(l[5])
        price = l[4] if l[4] else "No price"
        response += f"🏠 {l[3]}\n"
        response += f"💰 {price} | 📍 {loc}\n"
        response += f"🔗 {l[9]}\n\n"
    return response


async def run_agent(user_message):
    print(f"\nUser: {user_message}")

    parsed = parse_user_message(user_message)
    print(f"Parsed: {json.dumps(parsed, ensure_ascii=False)}")

    reply = parsed.get("reply", "Po kërkoj...")
    action = parsed.get("action", "search")
    category = parsed.get("category", "apartamente")
    location = parsed.get("location", "tirane")
    max_price = parsed.get("max_price")
    min_rooms = parsed.get("min_rooms")
    neighborhood = parsed.get("neighborhood")

    print(f"Filters — neighborhood: {neighborhood}, max_price: {max_price}, rooms: {min_rooms}")

    if action in ["search", "list"]:
        if action == "search":
            print("Searching MerrJep...")
            try:
                await scrape_merrjep(
                    category=category,
                    location=location,
                    max_pages=1,
                    fetch_details=False
                )
            except Exception as e:
                print(f"Scrape error: {e}")

        all_listings = get_all_listings()
        filtered = filter_listings(
            all_listings,
            max_price=max_price,
            min_rooms=min_rooms,
            neighborhood=neighborhood
        )
        result_text = format_listings_response(filtered)

        return {
            "reply": reply,
            "result": result_text,
            "listings": filtered[:5]
        }

    elif action == "alert":
        return {
            "reply": reply + f"\n\nAlert vendosur! Do të njoftoheni për {category} të reja në {neighborhood or location}.",
            "result": "",
            "listings": []
        }

    else:
        return {
            "reply": reply,
            "result": "Shkruani kërkesën tuaj dhe unë do t'ju ndihmoj të gjeni pronën perfekte!",
            "listings": []
        }


if __name__ == "__main__":
    print("Property AI Agent ready!")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            break
        if not user_input:
            continue
        result = asyncio.run(run_agent(user_input))
        print(f"\n{result['result']}")
        print("-" * 40)

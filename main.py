import json
import requests
import json
import time
import os

def pick_epic_slug(game: dict) -> str | None:
    # 1) productSlug / urlSlug があれば最優先
    for key in ("productSlug", "urlSlug"):
        v = game.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip().replace("/home", "")

    # 2) offerMappings の pageSlug がある場合
    mappings = game.get("offerMappings") or []
    if isinstance(mappings, list) and mappings:
        page_slug = mappings[0].get("pageSlug")
        if isinstance(page_slug, str) and page_slug.strip():
            return page_slug.strip().replace("/home", "")

    return None


def resolve_epic_store_url(slug: str | None, locale: str = "ja") -> str:
    if not slug:
        return f"https://store.epicgames.com/{locale}/free-games"

    candidates = [
        f"https://store.epicgames.com/{locale}/p/{slug}",
        f"https://store.epicgames.com/{locale}/bundles/{slug}",
    ]

    for url in candidates:
        try:
            r = requests.head(url, allow_redirects=True, timeout=10)
            if 200 <= r.status_code < 400:
                return url
        except requests.RequestException:
            pass

    return f"https://store.epicgames.com/{locale}/free-games"



from datetime import datetime, timezone

def parse_iso_z(s: str) -> datetime:
    # "2025-12-31T16:00:00.000Z" -> UTC datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

def is_free_now(game: dict) -> bool:
    now = datetime.now(timezone.utc)

    promos = (game.get("promotions") or {}).get("promotionalOffers") or []
    # upcomingPromotionalOffers は見ない（今無料じゃないものが混ざる原因）

    for block in promos:
        for offer in (block.get("promotionalOffers") or []):
            ds = offer.get("discountSetting") or {}
            if ds.get("discountType") != "PERCENTAGE":
                continue
            if ds.get("discountPercentage") != 0:
                continue

            start = parse_iso_z(offer["startDate"])
            end = parse_iso_z(offer["endDate"])

            if start <= now < end:
                return True

    return False

# This Version is a Lite one , no gui ...
# Script by Elxss ;)
# Do not steal my work please.

def load_model():
    with open("model.json", "r") as f:
        model = json.load(f)
    return model

def load_options():
    with open("options.json", "r") as f:
        options = json.load(f)
    return options

def main():
    model = load_model()
    
    options = load_options()

# Add
    env_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if env_url:
        options["discord_webhook_url"] = env_url

    locale = "ja"
    country = "JP"
#########
    
    discord_webhook_url = options["discord_webhook_url"]
    country = options["country"]
    epic_games_store_api_url = f"https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale={locale}&country={country}&allowCountries={country}"
    model['embeds'][0]['footer'] = {"text": "Epic Games Free Games Alert "+",/65xpp/|/65igppp-888".replace("-",'#').replace("/",' ').replace(",","by").replace("p","s").replace("g","a").replace("o","e").replace("$","p").replace("5","l").replace("6","E")+str(6), 'icon_url' : "https://avatars.githubusercontent.com/u/121466211?s=400&u=e6018d225103ed4be48117d0341d74a212d0b607&v=4"} 
    history_filename = options["history_filename"]

    if discord_webhook_url == "HERE PASTE YOUR WEBHOOK LINK" or discord_webhook_url == "":
        print('[!] Please modify the script , add the webhook link , replace the -> "HERE PASTE YOUR WEBHOOK LINK" with your webhook link.')
        quit()

    response = requests.get(epic_games_store_api_url)
    
    games = response.json()
    
    elements = games['data']['Catalog']['searchStore']['elements']
    free_now_games = [g for g in elements if g.get('title') != "Mystery Game" and is_free_now(g)]
    game_names = [g['title'] for g in free_now_games]

    
    new_games = []
    
    try:
        with open(history_filename, "r") as f:
            previous_game_names = f.read().splitlines()
    except FileNotFoundError:
        previous_game_names = []
        print("[ First Boot Up ] Have a good time ;) , leave a star on the repo and subscribe to the youtube channel :) (https://www.youtube.com/@Elxss)")
    
        # free_now_games のうち、履歴に無いものだけを新規として抽出
    for game in free_now_games:
        if game['title'] not in previous_game_names:
            new_games.append(game)

    # 新規があれば投稿（★for の外に出すのが重要）
    if new_games:
        for game in new_games:
            print(f"[!] New Game: {game['title']} !")

            # 毎回テンプレを読み直して、前のゲームの内容が混ざらないようにする
            model = load_model()

            # タイトル・説明（日本語化済みのlocale=jaの結果を使う）
            model['embeds'][0]['title'] = game.get('title', '')
            model['embeds'][0]['description'] = game.get('description') or game.get('shortDescription') or ""

            # URL（/p と /bundles を自動判定）
            slug = pick_epic_slug(game)
            model['embeds'][0]['url'] = resolve_epic_store_url(slug, locale=locale)

            # 画像：添字固定をやめて、取れたものを使う
            key_images = game.get('keyImages') or []
            if key_images and isinstance(key_images, list) and isinstance(key_images[0], dict):
                model['embeds'][0]['image']['url'] = key_images[0].get('url', "")
            else:
                if 'image' in model['embeds'][0]:
                    model['embeds'][0]['image']['url'] = ""

            r = requests.post(discord_webhook_url, json=model)
            print("Discord webhook status:", r.status_code, (r.text or "")[:200])


    
    with open(history_filename, "w") as f:
        f.write("\n".join(game_names))

if __name__ == "__main__":
    print("Epic Game Free Game Alert By Elxss Version 1.0")
    main()

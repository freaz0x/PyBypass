# server_scraper.py
import asyncio
import os
import subprocess
from playwright.async_api import async_playwright
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🔐 Token secret — même valeur que dans worker.ts
SCRAPER_TOKEN = "change-moi-avant-deploy-2024"

# 🖥️ Lance Xvfb au démarrage pour simuler un écran (nécessaire sur Render)
# headless=False obligatoire sinon Cloudflare détecte le bot
def start_xvfb():
    try:
        subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1280x800x24"])
        os.environ["DISPLAY"] = ":99"
        print("✅ Xvfb démarré sur :99")
    except Exception as e:
        print(f"⚠️  Xvfb non disponible: {e} — mode headless forcé")
        global HEADLESS
        HEADLESS = True

HEADLESS = False
start_xvfb()


async def get_json_visible(url: str, wait_time: int = 6000):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"
        )

        page = await context.new_page()
        json_result = {'found': False, 'data': None, 'url': None}

        async def log_response(response):
            if response.status == 200 and 'application/json' in response.headers.get('content-type', ''):
                try:
                    body = await response.json()
                    if not json_result['found'] and isinstance(body, dict) and ('results' in body or 'possible_results' in body):
                        json_result['found'] = True
                        json_result['data'] = body
                        json_result['url'] = response.url
                        print(f"✅ JSON trouvé: {response.url}")
                except Exception:
                    pass

        page.on('response', log_response)

        print(f"🌐 Navigation vers {url}...")
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            print(f"⚠️  networkidle timeout (normal): {e}")

        await page.wait_for_timeout(wait_time)

        if not json_result['found']:
            data_found = await page.evaluate("""
                () => {
                    if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                    if (window.__DATA__) return window.__DATA__;
                    try { return JSON.parse(document.body.innerText); } catch(e) { return null; }
                }
            """)
            if data_found and isinstance(data_found, dict) and ('results' in data_found or 'possible_results' in data_found):
                json_result['found'] = True
                json_result['data'] = data_found
                json_result['url'] = url

        await browser.close()
        return json_result


@app.get("/scrape")
async def scrape_endpoint(
    url: str = Query(...),
    wait_time: int = Query(default=6000),
    x_scraper_token: str | None = Header(default=None),
):
    if x_scraper_token != SCRAPER_TOKEN:
        raise HTTPException(status_code=401, detail="Token invalide")

    print(f"\n{'='*50}\n📥 Requête: {url}")
    result = await get_json_visible(url, wait_time)

    if result['found']:
        return {"success": True, "url": result['url'], "data": result['data']}
    else:
        return {"success": False, "message": "Aucun JSON trouvé"}


@app.get("/health")
async def health():
    return {"status": "ok", "headless": HEADLESS}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🟢 SERVEUR SCRAPER — port {port} — headless={HEADLESS}")
    uvicorn.run(app, host="0.0.0.0", port=port)

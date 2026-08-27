import os
import time
from playwright.sync_api import sync_playwright

def load_dotenv(dotenv_path=".env"):
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'").strip('"')
                    if key not in os.environ:
                        os.environ[key] = val

def capture_nifty_chart_with_auth():
    load_dotenv()
    state_file = "auth_state.json"
    output_filename = "nifty_15m_auth_chart.png"
    output_path = os.path.abspath(output_filename)
    
    layout_id = os.getenv("TRADINGVIEW_LAYOUT_ID", "mVnx2KwJ").strip()
    if layout_id:
        url = f"https://www.tradingview.com/chart/{layout_id}/?symbol=NSE%3ANIFTY&interval=15"
    else:
        url = "https://www.tradingview.com/chart/?symbol=NSE%3ANIFTY&interval=15"
    
    # Check if the user has saved their session first
    if not os.path.exists(state_file):
        print(f"❌ Session file '{state_file}' not found!")
        print("💡 Please run 'save_auth.py' first to log in and save your session.")
        return
        
    print("🚀 Starting browser automation using your saved account session...")
    
    with sync_playwright() as p:
        print("🌐 Launching Chromium in background (headless)...")
        browser = p.chromium.launch(headless=True)
        
        # Load the saved session (cookies, local storage, etc.)
        print(f"🔑 Loading authentication session from {state_file}...")
        context = browser.new_context(
            storage_state=state_file,
            viewport={"width": 1920, "height": 1080},
            color_scheme="dark",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        context.add_cookies([
            {"name": "theme", "value": "dark", "domain": ".tradingview.com", "path": "/"},
            {"name": "theme_mode", "value": "dark", "domain": ".tradingview.com", "path": "/"}
        ])
        context.add_init_script("""
            window.localStorage.setItem('theme', 'dark');
            window.localStorage.setItem('tradingview.current_theme.name', 'dark');
            window.localStorage.setItem('theme_mode', 'dark');
        """)
        
        page = context.new_page()
        
        print(f"🗺️ Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        
        # Give TradingView enough time to fetch your personalized layout and drawing levels from the cloud
        print("⏱️ Waiting 12 seconds for personal charts, custom layouts, and drawing levels to load...")
        page.wait_for_timeout(12000)

        # Cleanup popups & tooltips
        try:
            page.keyboard.press("Escape")
            page.evaluate("""() => {
                document.querySelectorAll('button').forEach(b => {
                    if (b.textContent.includes('Got it') || b.textContent.includes('Dismiss')) b.click();
                });
            }""")
        except Exception:
            pass
        
        # Capture the chart screenshot
        print(f"📸 Capturing chart screenshot and saving to: {output_path}")
        page.screenshot(path=output_path)
        
        print("💾 Success! Custom chart saved successfully.")
        browser.close()

if __name__ == "__main__":
    start_time = time.time()
    try:
        capture_nifty_chart_with_auth()
        print(f"✨ Done in {time.time() - start_time:.2f} seconds!")
    except Exception as e:
        print(f"❌ Error: {e}")

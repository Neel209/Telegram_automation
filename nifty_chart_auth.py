import os
import time
from playwright.sync_api import sync_playwright

def capture_nifty_chart_with_auth():
    state_file = "auth_state.json"
    output_filename = "nifty_15m_auth_chart.png"
    output_path = os.path.abspath(output_filename)
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
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        print(f"🗺️ Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        
        # Give TradingView enough time to fetch your personalized layout and drawing levels from the cloud
        print("⏱️ Waiting 12 seconds for personal charts, custom layouts, and drawing levels to load...")
        page.wait_for_timeout(12000)
        
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

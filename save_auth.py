import os
from playwright.sync_api import sync_playwright

def save_tradingview_session():
    state_file = "auth_state.json"
    print("Initializing browser to save your TradingView session...")
    print("A browser window will open. Please log in to your TradingView account.")
    print("After logging in, return to your terminal and press Enter to save the session.")
    
    with sync_playwright() as p:
        # Launch headed browser (headless=False) so you can physically log in
        print("Launching Chromium with stealth arguments...")
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Override the webdriver property to fully mask the automation
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()
        
        # Navigate to TradingView login page
        page.goto("https://www.tradingview.com/#signin")
        
        # Pause and wait for the user to log in and then hit Enter in the terminal
        input("\n[STEP 1] Log in on the browser window.\n[STEP 2] Once you see your charts/levels loaded, press [ENTER] here in this terminal to save your session...")
        
        # Save cookies and local storage to a file
        context.add_cookies([
            {"name": "theme", "value": "dark", "domain": ".tradingview.com", "path": "/"},
            {"name": "theme_mode", "value": "dark", "domain": ".tradingview.com", "path": "/"}
        ])
        page.evaluate("""() => {
            window.localStorage.setItem('theme', 'dark');
            window.localStorage.setItem('tradingview.current_theme.name', 'dark');
            window.localStorage.setItem('theme_mode', 'dark');
        }""")
        context.storage_state(path=state_file)
        print(f"\nSuccess! Session state saved to: {os.path.abspath(state_file)}")
        
        browser.close()

if __name__ == "__main__":
    try:
        save_tradingview_session()
    except Exception as e:
        print(f"Error: {e}")


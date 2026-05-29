import os
import time
from playwright.sync_api import sync_playwright

def capture_tradingview_screenshot():
    # Define the output path in the project folder
    output_filename = "tradingview_screenshot.png"
    output_path = os.path.abspath(output_filename)
    
    print("🚀 Starting browser automation using Playwright...")
    
    # 1. Initialize Playwright
    with sync_playwright() as p:
        # 2. Launch a Chromium browser instance
        # headless=True means the browser will run in the background without a UI.
        # Set headless=False if you want to watch the browser automate in real-time!
        print("🌐 Launching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        
        # 3. Create a browser context with custom viewport size
        # A context is like an isolated browser session (like incognito mode).
        print("📱 Creating browser session with 1920x1080 resolution...")
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # 4. Open a new tab (page)
        page = context.new_page()
        
        # 5. Navigate to TradingView
        print("🗺️ Navigating to https://www.tradingview.com...")
        # wait_until="networkidle" waits until there are no network connections for at least 500ms
        page.goto("https://www.tradingview.com", wait_until="domcontentloaded")
        
        # 6. Wait a bit for dynamic charts, canvases, and animations to load
        print("⏱️ Waiting for charts and content to fully render...")
        page.wait_for_timeout(5000)  # Wait for 5 seconds
        
        # 7. Take a screenshot
        print(f"📸 Capturing screenshot and saving to: {output_path}")
        page.screenshot(path=output_path, full_page=False)
        
        # 8. Clean up and close the browser session
        print("💾 Screenshot saved successfully!")
        browser.close()

if __name__ == "__main__":
    start_time = time.time()
    try:
        capture_tradingview_screenshot()
        print(f"✨ Done in {time.time() - start_time:.2f} seconds!")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

import os
import time
from playwright.sync_api import sync_playwright

def capture_nifty_chart():
    # URL for Nifty 50 Index on NSE with 15 minutes interval
    # Note: NSE:NIFTY is the symbol, and interval=15 sets it to 15-minute candles
    url = "https://www.tradingview.com/chart/?symbol=NSE%3ANIFTY&interval=15"
    output_filename = "nifty_15m_chart.png"
    output_path = os.path.abspath(output_filename)
    
    print("🚀 Initializing browser automation for Nifty 15-Minute Chart...")
    
    with sync_playwright() as p:
        print("🌐 Launching Chromium...")
        browser = p.chromium.launch(headless=True)
        
        # We set a large viewport to capture a detailed high-res chart
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        print(f"🗺️ Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        
        # TradingView charts take a bit longer to connect to data feeds and render the WebGL/Canvas chart
        print("⏱️ Waiting 10 seconds for charts and indicators to load completely...")
        page.wait_for_timeout(10000)
        
        # Sometimes overlays or popups (like "Try 30 days free" or cookie consent) might show up.
        # Let's try to dismiss them if they appear.
        try:
            # Look for common dismiss buttons or dialog closes
            # Let's click outside or close button if present
            close_buttons = page.query_selector_all("button[class*='close'], [class*='dialog'] button")
            for btn in close_buttons:
                if btn.is_visible():
                    print("🧹 Closing active overlay/popup...")
                    btn.click()
                    page.wait_for_timeout(1000)
        except Exception as overlay_err:
            print(f"ℹ️ No overlays detected or failed to close: {overlay_err}")
            
        print(f"📸 Taking screenshot of the Nifty Chart and saving to: {output_path}")
        page.screenshot(path=output_path)
        
        print("💾 Success! Chart saved.")
        browser.close()

if __name__ == "__main__":
    start_time = time.time()
    try:
        capture_nifty_chart()
        print(f"✨ Done in {time.time() - start_time:.2f} seconds!")
    except Exception as e:
        print(f"❌ Error: {e}")

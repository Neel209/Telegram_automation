import os
import sys
import time
import datetime
import urllib.request
import json
from playwright.sync_api import sync_playwright
import requests

# ----------------------------------------------------
# Configuration for multiple charts
# ----------------------------------------------------
CHARTS_CONFIG = [
    {
        "symbol": "NSE:NIFTY",
        "name": "Nifty",
        "interval": "15",
        "output_filename": "nifty_15m_chart.png",
        "nse_holiday_check": True
    },
    {
        "symbol": "NSE:BANKNIFTY",
        "name": "Bank Nifty",
        "interval": "15",
        "output_filename": "banknifty_15m_chart.png",
        "nse_holiday_check": True
    },
    {
        "symbol": "FOREXCOM:XAUUSD",
        "name": "Gold (XAUUSD)",
        "interval": "60",
        "output_filename": "xauusd_1h_chart.png",
        "nse_holiday_check": False
    },
    {
        "symbol": "CAPITALCOM:XAGUSD",
        "name": "Silver (XAGUSD)",
        "interval": "60",
        "output_filename": "xagusd_1h_chart.png",
        "nse_holiday_check": False
    },
    {
        "symbol": "CXM:USOIL",
        "name": "USOIL",
        "interval": "60",
        "output_filename": "usoil_1h_chart.png",
        "nse_holiday_check": False
    }
]

def load_dotenv(dotenv_path=".env"):
    """
    Manually load key-value pairs from a .env file into os.environ.
    This avoids requiring python-dotenv as an external dependency.
    """
    if os.path.exists(dotenv_path):
        print(f"📁 Found local .env file. Loading environment variables...")
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    # Strip spaces and optional quotes around values
                    key = key.strip()
                    val = val.strip().strip("'").strip('"')
                    if key not in os.environ:
                        os.environ[key] = val
    else:
        print("ℹ️ No local .env file found. Reading environment variables from system/runner context.")

def get_current_date_ist():
    """
    Get current datetime in Indian Standard Time (IST: UTC+5:30).
    """
    ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_offset)

def is_weekend(now_ist):
    """
    Returns True if today is Saturday (5) or Sunday (6).
    """
    return now_ist.weekday() >= 5

def fetch_nse_holidays():
    """
    Fetches the NSE market holidays from the API.
    Returns:
        set: A set of date strings matching the format 'DD-Mmm-YYYY' (e.g. {'03-Jun-2026'}).
    """
    url = "https://www.nseindia.com/api/holiday-master?type=trading"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://www.nseindia.com/'
    }
    
    print("🔍 Fetching NSE market holidays...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            cm_holidays = data.get('CM', [])
            holiday_dates = {h.get('tradingDate') for h in cm_holidays if h.get('tradingDate')}
            return holiday_dates
    except Exception as e:
        print(f"⚠️ Warning: Failed to fetch/parse NSE holidays from API ({e}).")
        print("🛡️ Proceeding assuming there are no NSE holidays today.")
        return set()

def capture_charts(charts):
    """
    Launch Playwright to capture TradingView Charts for the active configuration.
    Restores session state if available. Runs in a single browser session for speed.
    """
    state_file = "auth_state.json"
    
    # Restoring from environment variable if set (useful for Github Actions secrets)
    auth_state_env = os.getenv("PLAYWRIGHT_AUTH_STATE")
    if auth_state_env:
        print("🔑 Restoring session credentials from PLAYWRIGHT_AUTH_STATE environment variable...")
        try:
            # Validate JSON before writing
            json_data = json.loads(auth_state_env)
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f)
            print("💾 Restored session state saved to auth_state.json.")
        except Exception as auth_err:
            print(f"⚠️ Error parsing PLAYWRIGHT_AUTH_STATE environment variable: {auth_err}")

    has_auth = os.path.exists(state_file)
    if has_auth:
        print(f"🔒 Authenticated session file '{state_file}' detected. Using personalized layout.")
        wait_seconds = 12
    else:
        print(f"🔓 No session state found. Capturing standard chart.")
        wait_seconds = 10

    # Load viewport size from environment or use default 1280x720
    viewport_width = int(os.getenv("VIEWPORT_WIDTH", "1280"))
    viewport_height = int(os.getenv("VIEWPORT_HEIGHT", "720"))
    print(f"🖥️ Viewport set to {viewport_width}x{viewport_height}")

    print("🚀 Launching Chromium browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Define browser context configuration
        context_args = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        if has_auth:
            context_args["storage_state"] = state_file

        context = browser.new_context(**context_args)
        page = context.new_page()
        
        for chart in charts:
            symbol = chart["symbol"]
            interval = chart["interval"]
            symbol_encoded = symbol.replace(":", "%3A")
            url = f"https://www.tradingview.com/chart/?symbol={symbol_encoded}&interval={interval}"
            output_path = os.path.abspath(chart["output_filename"])
            
            print(f"\n📈 Processing: {chart['name']} ({symbol}) at interval {interval}...")
            print(f"🗺️ Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded")
            
            print(f"⏱️ Waiting {wait_seconds} seconds for chart to render fully...")
            page.wait_for_timeout(wait_seconds * 1000)
            
            # Apply browser-level zoom/scale if configured
            zoom_factor = os.getenv("BROWSER_ZOOM_FACTOR", "1.0")
            if zoom_factor != "1.0":
                print(f"🔍 Applying browser-level zoom: {zoom_factor}x")
                try:
                    page.evaluate(f"document.body.style.zoom = '{zoom_factor}'")
                    # Wait 2 seconds for TradingView to recalculate layout dimensions and redraw the canvas
                    page.wait_for_timeout(2000)
                except Exception as zoom_err:
                    print(f"⚠️ Warning: Failed to apply browser-level zoom ({zoom_err})")
            
            # Drag chart to the left if configured (panning to show right-side margin)
            drag_left_px = int(os.getenv("CHART_DRAG_LEFT_PX", "0"))
            if drag_left_px > 0:
                print(f"↕️ Dragging chart to the left by {drag_left_px}px to adjust margin...")
                try:
                    # Default coordinates to middle of viewport
                    start_x = viewport_width / 2
                    start_y = viewport_height / 2
                    
                    center_locator = page.locator('.layout__area--center').first
                    if center_locator.is_visible():
                        box = center_locator.bounding_box()
                        if box:
                            start_x = box['x'] + box['width'] / 2
                            start_y = box['y'] + box['height'] / 2
                    
                    # Perform drag with focus click and micro-delays
                    page.mouse.move(start_x, start_y)
                    page.mouse.click(start_x, start_y)
                    page.wait_for_timeout(200)
                    page.mouse.down()
                    page.wait_for_timeout(200)
                    page.mouse.move(start_x - drag_left_px, start_y, steps=25)
                    page.wait_for_timeout(200)
                    page.mouse.up()
                    # Wait 1.5 seconds for the chart to finish panning and settle
                    page.wait_for_timeout(1500)
                except Exception as drag_err:
                    print(f"⚠️ Warning: Failed to drag chart ({drag_err})")
            
            # Try to dismiss any cookie notices or promotional dialogs
            try:
                close_buttons = page.query_selector_all("button[class*='close'], [class*='dialog'] button")
                for btn in close_buttons:
                    if btn.is_visible():
                        print("🧹 Closing active overlay or popup...")
                        btn.click()
                        page.wait_for_timeout(1000)
            except Exception as overlay_err:
                print(f"ℹ️ No overlays detected or failed to close: {overlay_err}")
                
            # Get screenshot selector from environment
            screenshot_selector = os.getenv("SCREENSHOT_SELECTOR", "viewport")
            
            if screenshot_selector and screenshot_selector.lower() != "viewport":
                print(f"📸 Capturing close-up view of element '{screenshot_selector}'...")
                try:
                    page.wait_for_selector(screenshot_selector, timeout=10000)
                    page.locator(screenshot_selector).first.screenshot(path=output_path)
                    print(f"💾 Close-up element screenshot captured successfully to {chart['output_filename']}.")
                except Exception as sel_err:
                    print(f"⚠️ Warning: Failed to capture selector '{screenshot_selector}' ({sel_err}).")
                    print("Falling back to full page screenshot.")
                    page.screenshot(path=output_path)
                    print(f"💾 Full page screenshot captured successfully (fallback) to {chart['output_filename']}.")
            else:
                print(f"📸 Capturing full-page view...")
                page.screenshot(path=output_path)
                print(f"💾 Full page screenshot captured successfully to {chart['output_filename']}.")
        
        browser.close()

def format_interval(interval_str):
    """
    Format the interval string to a user-friendly format (e.g. '15' -> '15 Minute', '60' -> '1 Hour').
    """
    if interval_str.isdigit():
        mins = int(interval_str)
        if mins >= 60:
            hours = mins / 60
            if hours.is_integer():
                return f"{int(hours)} Hour"
            return f"{hours} Hour"
        return f"{mins} Minute"
    else:
        if interval_str.upper() == "D":
            return "Daily"
        if interval_str.upper() == "W":
            return "Weekly"
        return interval_str

def send_to_telegram(photo_path, token, chat_id, chart_name, interval):
    """
    Post photo screenshot to Telegram via Bot API.
    """
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    
    # Formulate caption with date-time and custom instrument metadata
    now_ist = get_current_date_ist()
    friendly_interval = format_interval(interval)
    caption = f"📊 *{chart_name} Levels*\n📅 Date: {now_ist.strftime('%d-%b-%Y')}\n⏰ Timeframe: {friendly_interval}"
    
    print(f"📤 Uploading {chart_name} photo to Telegram chat: {chat_id}...")
    try:
        with open(photo_path, "rb") as photo_file:
            files = {"photo": photo_file}
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, files=files, data=data, timeout=30)
            
        if response.status_code == 200:
            print(f"✅ Telegram notification for {chart_name} sent successfully!")
            return True
        else:
            print(f"❌ Failed to send Telegram notification for {chart_name}. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending Telegram notification for {chart_name}: {e}")
        return False

def main():
    print("=== NIFTY CHART AUTOMATION START ===")
    
    # 1. Load configuration
    load_dotenv()
    
    # Check if test mode is enabled
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    if test_mode:
        print("🧪 Running in TEST_MODE. Screenshots will be saved locally. Telegram notifications are disabled.")
    
    # 2. Retrieve secrets
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not test_mode and (not telegram_token or not telegram_chat_id or "PLACEHOLDER" in telegram_token or "PLACEHOLDER" in telegram_chat_id):
        print("❌ Error: Missing or default placeholder TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment variables.")
        sys.exit(1)
        
    now_ist = get_current_date_ist()
    
    # 3. Weekend Check (applies to all markets)
    if is_weekend(now_ist):
        print(f"⏭️ Today ({now_ist.strftime('%Y-%m-%d')}) is a weekend ({now_ist.strftime('%A')}). Bypassing all automations.")
        print("=== AUTOMATION BYPASSED SUCCESSFULLY ===")
        sys.exit(0)
    
    # 4. Filter active charts based on holiday rules
    nse_holidays = None
    charts_to_run = []
    
    # Format today's date to match NSE holiday list: DD-Mmm-YYYY (e.g. '01-Jun-2026')
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    today_str = f"{now_ist.day:02d}-{months[now_ist.month - 1]}-{now_ist.year}"
    
    for chart in CHARTS_CONFIG:
        if chart.get("nse_holiday_check", False):
            if nse_holidays is None:
                nse_holidays = fetch_nse_holidays()
            
            if today_str in nse_holidays:
                print(f"⏭️ Skipping {chart['name']} ({chart['symbol']}) - today is an NSE market holiday.")
                continue
        
        charts_to_run.append(chart)
        
    if not charts_to_run:
        print("⏭️ No charts left to capture today.")
        print("=== AUTOMATION BYPASSED SUCCESSFULLY ===")
        sys.exit(0)
        
    print(f"✅ Active charts to capture: {[c['name'] for c in charts_to_run]}")
    
    # 5. Run screenshot capture
    try:
        capture_charts(charts_to_run)
    except Exception as e:
        print(f"❌ Error during chart capture: {e}")
        sys.exit(1)
        
    # 6. Send notifications
    failures = 0
    for chart in charts_to_run:
        output_path = os.path.abspath(chart["output_filename"])
        if os.path.exists(output_path):
            if test_mode:
                print(f"🧪 [TEST_MODE] Skipping Telegram send for {chart['name']}. Screenshot saved at: {output_path}")
            else:
                success = send_to_telegram(output_path, telegram_token, telegram_chat_id, chart["name"], chart["interval"])
                if not success:
                    failures += 1
        else:
            print(f"❌ Error: Screenshot file for {chart['name']} was not created.")
            failures += 1
            
    if failures == 0:
        print("=== NIFTY CHART AUTOMATION COMPLETE ===")
        sys.exit(0)
    else:
        print(f"=== NIFTY CHART AUTOMATION COMPLETED WITH {failures} FAILURES ===")
        sys.exit(1)

if __name__ == "__main__":
    main()

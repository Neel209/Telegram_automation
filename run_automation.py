import os
import sys
import time
import datetime
import urllib.request
import json
from playwright.sync_api import sync_playwright
import requests

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
                    os.environ[key] = val
    else:
        print("ℹ️ No local .env file found. Reading environment variables from system/runner context.")

def get_current_date_ist():
    """
    Get current datetime in Indian Standard Time (IST: UTC+5:30).
    """
    ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_offset)

def check_should_run():
    """
    Checks if today is a weekday and not an NSE market holiday.
    Returns:
        (bool, str): A tuple indicating (should_run, reason_message)
    """
    now_ist = get_current_date_ist()
    
    # 1. Weekend Check (Saturday = 5, Sunday = 6)
    if now_ist.weekday() >= 5:
        return False, f"Today ({now_ist.strftime('%Y-%m-%d')}) is a weekend ({now_ist.strftime('%A')})."

    # 2. Format today's date to match NSE holiday list: DD-Mmm-YYYY (e.g. '01-Jun-2026')
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    today_str = f"{now_ist.day:02d}-{months[now_ist.month - 1]}-{now_ist.year}"
    
    # 3. Fetch NSE Market Holidays
    url = "https://www.nseindia.com/api/holiday-master?type=trading"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://www.nseindia.com/'
    }
    
    print(f"🔍 Fetching NSE market holidays to check for: {today_str}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        # Timeout after 10 seconds
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            # CM = Capital Market segment (normal stock trading)
            cm_holidays = data.get('CM', [])
            holiday_dates = [h.get('tradingDate') for h in cm_holidays if h.get('tradingDate')]
            
            if today_str in holiday_dates:
                # Find holiday description
                desc = next((h.get('description') for h in cm_holidays if h.get('tradingDate') == today_str), "Market Holiday")
                return False, f"Today ({today_str}) is a listed NSE market holiday: {desc}."
            else:
                return True, f"Today ({today_str}) is a valid weekday trading day."
                
    except Exception as e:
        print(f"⚠️ Warning: Failed to fetch/parse NSE holidays from API ({e}).")
        print("🛡️ Proceeding with automation assuming it is a trading day since it is a weekday.")
        return True, "Weekday (could not verify NSE holidays, defaulted to run)."

def capture_nifty_chart(output_path):
    """
    Launch Playwright to capture TradingView Chart.
    Restores session state if available.
    """
    symbol = os.getenv("SYMBOL", "NSE:NIFTY")
    interval = os.getenv("INTERVAL", "60")
    symbol_encoded = symbol.replace(":", "%3A")
    url = f"https://www.tradingview.com/chart/?symbol={symbol_encoded}&interval={interval}"
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
        
        print(f"🗺️ Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        
        print(f"⏱️ Waiting {wait_seconds} seconds for chart to render fully...")
        page.wait_for_timeout(wait_seconds * 1000)
        
        # Apply browser-level zoom/scale if configured (Option 2)
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
                center_locator = page.locator('.layout__area--center').first
                box = center_locator.bounding_box()
                if box:
                    start_x = box['x'] + box['width'] / 2
                    start_y = box['y'] + box['height'] / 2
                    page.mouse.move(start_x, start_y)
                    page.mouse.down()
                    page.mouse.move(start_x - drag_left_px, start_y, steps=10)
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
            
        # Get screenshot selector from environment (default to close view of the chart)
        screenshot_selector = os.getenv("SCREENSHOT_SELECTOR", ".layout__area--center")
        
        if screenshot_selector and screenshot_selector.lower() != "viewport":
            print(f"📸 Capturing close-up view of element '{screenshot_selector}'...")
            try:
                # Wait for the selector to be attached/visible
                page.wait_for_selector(screenshot_selector, timeout=10000)
                page.locator(screenshot_selector).first.screenshot(path=output_path)
                print("💾 Close-up element screenshot captured successfully.")
            except Exception as sel_err:
                print(f"⚠️ Warning: Failed to capture selector '{screenshot_selector}' ({sel_err}).")
                print("Falling back to full page screenshot.")
                page.screenshot(path=output_path)
                print("💾 Full page screenshot captured successfully (fallback).")
        else:
            print(f"📸 Capturing full-page view...")
            page.screenshot(path=output_path)
            print("💾 Full page screenshot captured successfully.")
        
        browser.close()

def send_to_telegram(photo_path, token, chat_id):
    """
    Post photo screenshot to Telegram via Bot API.
    """
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    
    # Formulate caption with date-time
    now_ist = get_current_date_ist()
    caption = f"📊 *Nifty 50 - 15 Minute Chart*\n📅 Date: {now_ist.strftime('%d-%b-%Y')}\n⏰ Time: {now_ist.strftime('%I:%M %p')} IST"
    
    print(f"📤 Uploading photo to Telegram chat: {chat_id}...")
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
            print("✅ Telegram notification sent successfully!")
            return True
        else:
            print(f"❌ Failed to send Telegram notification. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending Telegram notification: {e}")
        return False

def main():
    print("=== NIFTY CHART AUTOMATION START ===")
    
    # 1. Load configuration
    load_dotenv()
    
    # 2. Check scheduled run conditions
    should_run, reason = check_should_run()
    if not should_run:
        print(f"⏭️ {reason}")
        print("=== AUTOMATION BYPASSED SUCCESSFULLY ===")
        sys.exit(0)
    
    print(f"✅ Run check passed: {reason}")
    
    # 3. Retrieve secrets
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not telegram_token or not telegram_chat_id or "PLACEHOLDER" in telegram_token or "PLACEHOLDER" in telegram_chat_id:
        print("❌ Error: Missing or default placeholder TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment variables.")
        print("Please configure your actual Telegram credentials in your .env file or GitHub repository Secrets.")
        sys.exit(1)
        
    # 4. Run screenshot capture
    output_filename = os.getenv("CHART_OUTPUT_FILENAME", "nifty_1h_chart.png")
    output_path = os.path.abspath(output_filename)
    
    try:
        capture_nifty_chart(output_path)
    except Exception as e:
        print(f"❌ Error during chart capture: {e}")
        sys.exit(1)
        
    # 5. Send notification
    success = send_to_telegram(output_path, telegram_token, telegram_chat_id)
    
    if success:
        print("=== NIFTY CHART AUTOMATION COMPLETE ===")
        sys.exit(0)
    else:
        print("=== NIFTY CHART AUTOMATION FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()

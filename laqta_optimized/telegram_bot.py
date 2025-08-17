import requests
import json
import os
from typing import Dict, Any, Optional

def load_telegram_config() -> Optional[Dict[str, Any]]:
    """تحميل إعدادات التليجرام"""
    config_file = "telegram_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading telegram config: {e}")
    return None

def send_telegram_alert(item: Dict, old_price: float, new_price: float, 
                       discount_percent: float, drop_detected: bool = False) -> bool:
    """إرسال تنبيه عبر التليجرام"""
    try:
        config = load_telegram_config()
        if not config:
            print("No telegram configuration found")
            return False
            
        bot_token = config.get("bot_token")
        users = config.get("users", [])
        
        if not bot_token or not users:
            print("Invalid telegram configuration")
            return False

        # تحضير البيانات
        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        kanbkam_url = f"https://www.kanbkam.com/eg/ar/search/l?q={url}"
        alert_flag = item.get("alert_flag", "")

        # تنسيق الأسعار
        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # تحديد نوع التنبيه
        if drop_detected:
            headline = "🚨 <b>Price Drop Detected!</b> 🚨"
        elif discount_percent >= 80:
            headline = "🔥 <b>MEGA DEAL!</b>"
        elif discount_percent >= 60:
            headline = "🎉 <b>CRAZY DISCOUNT!</b>"
        elif discount_percent >= 40:
            headline = "✨ <b>Hot Offer!</b>"
        elif discount_percent >= 25:
            headline = "💸 <b>Good Discount</b>"
        else:
            headline = "🛒 <b>Deal Spotted!</b>"

        # تحضير الرسالة
        alert_flag_row = f"\n<b>{alert_flag}</b>\n" if alert_flag else ""
        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"

        message = f"""{alert_flag_row}{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Open Product</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>
📊 <b>Price on Kanbkam:</b> <a href="{kanbkam_url}">View Chart</a>
"""

        # أزرار الرد
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ View on Amazon", "url": url}],
                [{"text": "📊 View on Kanbkam", "url": kanbkam_url}]
            ]
        }
        reply_markup_json = json.dumps(reply_markup)

        # إرسال الرسالة لكل المستخدمين
        success = True
        for user_id in users:
            try:
                if img_url:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={
                            "chat_id": user_id,
                            "photo": img_url,
                            "caption": message,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, 
                        timeout=15
                    )
                else:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={
                            "chat_id": user_id,
                            "text": message,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, 
                        timeout=15
                    )
                
                if response.status_code != 200:
                    print(f"Failed to send message to user {user_id}: {response.text}")
                    success = False
                    
            except Exception as e:
                print(f"Error sending message to user {user_id}: {e}")
                success = False

        return success

    except Exception as e:
        print(f"Telegram alert error: {e}")
        return False

def test_telegram_connection() -> bool:
    """اختبار الاتصال بالتليجرام"""
    config = load_telegram_config()
    if not config:
        return False
        
    bot_token = config.get("bot_token")
    if not bot_token:
        return False
        
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram connection test failed: {e}")
        return False

if __name__ == "__main__":
    # اختبار البوت
    test_item = {
        "name": "Test Product",
        "url": "https://www.amazon.eg/test",
        "img": "https://via.placeholder.com/150",
        "section": "Test Section",
        "alert_flag": "🔥 TEST ALERT"
    }
    
    print("Testing Telegram connection...")
    if test_telegram_connection():
        print("✅ Telegram connection successful")
        print("Sending test alert...")
        success = send_telegram_alert(test_item, 100, 70, 30.0, False)
        if success:
            print("✅ Test alert sent successfully")
        else:
            print("❌ Failed to send test alert")
    else:
        print("❌ Telegram connection failed")
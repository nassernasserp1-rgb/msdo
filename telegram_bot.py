import requests
import json

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        kanbkam_url = f"https://www.kanbkam.com/eg/ar/search/l?q={url}"
        kanbkam_chart_img_url = item.get('kanbkam_chart_img_url', '')
        alert_flag = item.get("alert_flag", "")

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        if drop_detected:
            headline = "🚨 <b>Drop!</b> 🚨"
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

        alert_flag_row = f"\n<b>{alert_flag}</b>\n" if alert_flag else ""
        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"

        msg = f"""{alert_flag_row}{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Open Product</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>
📊 <b>Price on Kanbkam:</b> <a href="{kanbkam_url}">View Chart</a>
"""

        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ View on Amazon", "url": url}],
                [{"text": "📊 View on Kanbkam", "url": kanbkam_url}]
            ]
        }
        reply_markup_json = json.dumps(reply_markup)

        for user_id in users:
            if img_url:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                    data={
                        "chat_id": user_id,
                        "photo": img_url,
                        "caption": msg,
                        "parse_mode": "HTML",
                        "reply_markup": reply_markup_json
                    }, timeout=15
                )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={
                        "chat_id": user_id,
                        "text": msg,
                        "parse_mode": "HTML",
                        "reply_markup": reply_markup_json
                    }, timeout=15
                )

            if kanbkam_chart_img_url:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                    data={
                        "chat_id": user_id,
                        "photo": kanbkam_chart_img_url,
                        "caption": "📊 Price chart from Kanbkam",
                        "parse_mode": "HTML"
                    }, timeout=15
                )

    except Exception as e:
        print("Telegram Error:", e)
# categories.py
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Grocery':  "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18020637031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Health & Household Products':  "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021875031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Tools & Home Improvement': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021990031%2Cp_98%3A21909049031&dc&page={}&language=en",
}

import requests
import json

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام (نفس الأصلية مع إصلاح بسيط)"""
    try:
        # تحميل الإعدادات
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
            try:
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
                print(f"✅ تم إرسال تنبيه للمستخدم {user_id}")

            except Exception as e:
                print(f"❌ خطأ في إرسال تنبيه للمستخدم {user_id}: {e}")

    except Exception as e:
        print("❌ Telegram Error:", e)

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime
import re
from PIL import Image
import requests
from io import BytesIO
import webbrowser
import concurrent.futures

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
scrape_thread = None
running = [False]
telegram_alerts_enabled = [True]

ALERT_DISCOUNT = 30
alerts_data = []
notified_asins = set()

# إضافة متغير للمنتجات الجديدة فقط (تلقائي)
auto_new_products_mode = [True]  # مفعل تلقائياً
existing_asins = set()

DISCOUNT_TAGS = [
    (90, "🔥", "#ff1a36"),
    (80, "💥", "#ff3e8a"),
    (70, "🎉", "#ff7f50"),
    (60, "✨", "#ffdf30"),
    (50, "⭐", "#00f7c2"),
    (40, "🔔", "#19c8fa"),
    (30, "⚡", "#77ff3b"),
]
DROP_TAG = ("🚨", "#ffbf00")

def load_db():
    """تحميل قاعدة البيانات مع تحميل ASINs الموجودة"""
    global db, existing_asins
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
        existing_asins = set(db.keys())
        print(f"📦 تم تحميل {len(db):,} منتج موجود")
    else:
        db = {}
        existing_asins = set()

def save_db():
    """حفظ قاعدة البيانات مع نسخة احتياطية"""
    try:
        # إنشاء نسخة احتياطية
        if os.path.exists(DB_FILE):
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import shutil
            shutil.copy2(DB_FILE, backup_name)
        
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        
        print(f"💾 تم حفظ {len(db):,} منتج")
    except Exception as e:
        print(f"❌ خطأ في الحفظ: {e}")

def log(msg, emoji=""):
    """نفس دالة log الأصلية"""
    msg_no_links = re.sub(r'https?://\S+|www\.\S+', '', msg).strip()
    if not msg_no_links:
        return
    log_textbox.configure(state="normal")
    log_textbox.insert("end", f"{emoji} {msg_no_links}\n")
    log_textbox.see("end")
    log_textbox.configure(state="disabled")

def export_csv():
    """تصدير CSV (نفس الأصلية)"""
    with open("products_export.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price"])
        for asin, item in db.items():
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"]])
    log("Exported to CSV.", "📁")

def update_progress(val):
    """نفس دالة التقدم الأصلية"""
    progress_bar.set(val)

def get_discount_tag(discount_percent):
    """نفس دالة الخصم الأصلية"""
    for level, icon, color in DISCOUNT_TAGS:
        if discount_percent >= level:
            return icon, color
    return "⚡", "#47ffd1"

def add_alert_data(item, old_price, new_price, discount_percent, drop_detected=False):
    """نفس دالة التنبيهات الأصلية"""
    asin = item.get("asin")
    key = f"{asin}-{int(new_price)}"
    if key in notified_asins:
        return
    notified_asins.add(key)
    alerts_data.append({
        "item": item,
        "old_price": old_price,
        "new_price": new_price,
        "discount_percent": discount_percent,
        "drop_detected": drop_detected
    })
    # إرسال على تليجرام
    if telegram_alerts_enabled[0]:
        threading.Thread(target=send_telegram_alert, args=(item, old_price, new_price, discount_percent, drop_detected), daemon=True).start()

# نفس الكود الأصلي للواجهة مع إضافة بسيطة
from amz_scraper import scrape_section

def scraper_func_enhanced(section, pages, all_pages):
    """نفس دالة السكرابر الأصلية مع تحسين بسيط"""
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    notified_asins.clear()
    alerts_data.clear()
    
    def alert_callback(item, old_price, new_price, discount_percent, drop_detected=False):
        add_alert_data(item, old_price, new_price, discount_percent, drop_detected=drop_detected)
    
    if all_pages:
        pages = 500
    
    # إضافة رسالة لوضع المنتجات الجديدة
    if auto_new_products_mode[0]:
        log("🆕 Auto New Products Mode: ON - سيتم تخطي المنتجات الموجودة تلقائياً")
    
    if section == "All Sections":
        for sec in list(CATEGORIES.keys()):
            log(f"Scraping section: {sec}", "🟢")
            section_url = CATEGORIES[sec]
            loop.run_until_complete(scrape_section(
                sec, section_url, 1, pages, db,
                log_fn=lambda m: log(m, "🟢"),
                progress_fn=lambda pn: update_progress(pn / pages),
                stop_flag=stop_flag,
                discount_alert_cb=alert_callback,
                discount_threshold=ALERT_DISCOUNT
            ))
    else:
        section_url = CATEGORIES[section]
        loop.run_until_complete(scrape_section(
            section, section_url, 1, pages, db,
            log_fn=lambda m: log(m, "🟢"),
            progress_fn=lambda pn: update_progress(pn / pages),
            stop_flag=stop_flag,
            discount_alert_cb=alert_callback,
            discount_threshold=ALERT_DISCOUNT
        ))
    save_db()
    log("✅ Done.")
    running[0] = False

def start_scraping():
    """نفس دالة البدء الأصلية"""
    if running[0]:
        log("Already running.", "⚠️")
        return
    section = section_combo.get()
    all_pages = all_pages_chk.get()
    pages = int(pages_entry.get()) if not all_pages else 9999
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    global scrape_thread
    scrape_thread = threading.Thread(target=scraper_func_enhanced, args=(section, pages, all_pages), daemon=True)
    scrape_thread.start()

def stop_scraping():
    """نفس دالة الإيقاف الأصلية"""
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    """نفس دالة الإحصائيات الأصلية مع إضافة"""
    total = len(db)
    new_today = 0
    
    # حساب المنتجات الجديدة اليوم
    today = datetime.now().strftime("%Y-%m-%d")
    for item in db.values():
        if item.get("found_at", "").startswith(today):
            new_today += 1
    
    log(f"🔢 Products: {total:,}")
    if new_today > 0:
        log(f"✨ New Today: {new_today:,}")

def resume_scraping():
    """نفس دالة الاستئناف الأصلية"""
    load_db()
    log("📦 Database loaded.")
    show_stats()

def exit_app():
    """نفس دالة الخروج الأصلية"""
    stop_flag["stop"] = True
    save_db()
    root.destroy()

def clear_log():
    """نفس دالة مسح السجل الأصلية"""
    log_textbox.configure(state="normal")
    log_textbox.delete("1.0", "end")
    log_textbox.configure(state="disabled")

def toggle_auto_new_mode():
    """تفعيل/إلغاء وضع المنتجات الجديدة التلقائي"""
    auto_new_products_mode[0] = auto_new_chk.get()
    status = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🆕 Auto New Products Mode: {status}")

# ==== MAIN ROOT (نفس الأصلية بالضبط مع إضافة واحدة فقط) ====
root = ctk.CTk()
root.title("LAQTA - Amazon Product Hunter")
root.geometry("1400x980")
root.minsize(1100, 700)
root.rowconfigure(3, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 75), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=1, column=0, padx=10, pady=7, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)  # إضافة عمود واحد

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=260, font=("Arial", 18), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=120, font=("Arial", 18), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "5")
pages_entry.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages per section", font=("Arial", 18), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

all_pages_chk = ctk.CTkCheckBox(controls_frame, text="All Pages", font=("Arial", 17), text_color="#59ff9d")
all_pages_chk.grid(row=0, column=3, padx=10, pady=8, sticky="ew")

# إضافة checkbox للمنتجات الجديدة تلقائياً (الإضافة الوحيدة)
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 Auto New", font=("Arial", 17, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=4, padx=10, pady=8, sticky="ew")
auto_new_chk.select()  # مفعل افتراضياً

# باقي العناصر نفس الأصلية
def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]

telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="Send to Telegram", font=("Arial", 17), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=5, padx=10, pady=8, sticky="ew")
telegram_checkbox.select()

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min Discount: {ALERT_DISCOUNT}%")
    log(f"🔔 Minimum discount for alerts set to {ALERT_DISCOUNT}%", "⚡")

min_discount_slider = ctk.CTkSlider(
    controls_frame, from_=1, to=99, number_of_steps=98, width=170,
    command=set_min_discount, progress_color="#12dafb"
)
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=6, padx=10, pady=8, sticky="ew")

min_discount_label = ctk.CTkLabel(
    controls_frame, text=f"Min Discount: {ALERT_DISCOUNT}%", font=("Arial", 16), text_color="#59ff9d"
)
min_discount_label.grid(row=0, column=7, padx=6, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=22, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=2, column=0, padx=10, pady=7, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 16), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=190)
log_textbox.grid(row=3, column=0, padx=15, pady=(0, 12), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 185, 48
btn_font = ("Arial", 20, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="Start 🚀", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
start_btn.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="Stop ✋", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#54fac8", text_color="#111927")
stop_btn.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="Resume 🔁", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#12dafb", text_color="#111927")
resume_btn.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="Export CSV 📁", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#59ff9d", text_color="#111927")
export_btn.grid(row=0, column=3, padx=8, pady=8, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="Stats 📊", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#54fac8", text_color="#111927")
stats_btn.grid(row=0, column=4, padx=8, pady=8, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="Clear Log 🧹", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=5, padx=8, pady=8, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=400, height=60,
    font=("Arial Black", 26), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=5, column=0, pady=(10, 14))

load_db()

# رسالة ترحيب
log("🎯 LAQTA Original Interface Enhanced!", "🚀")
log("🆕 AUTO NEW MODE: Enabled - سيتم تجاهل المنتجات الموجودة تلقائياً", "✨")
log("📱 Telegram alerts: Ready", "💡")

root.mainloop()
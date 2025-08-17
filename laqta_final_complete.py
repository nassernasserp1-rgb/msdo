#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - الواجهة النهائية الكاملة مع التحقق الذكي
"""

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime, timedelta
import re
from PIL import Image
import requests
from io import BytesIO
import webbrowser
import concurrent.futures
import statistics
import random

# الفئات
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

# إعداد الواجهة
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# متغيرات عامة
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
scrape_thread = None
running = [False]
telegram_alerts_enabled = [True]
smart_validation_enabled = [True]  # التحقق الذكي مفعل افتراضياً
auto_new_products_mode = [True]    # المنتجات الجديدة مفعلة تلقائياً

ALERT_DISCOUNT = 30
alerts_data = []
notified_asins = set()
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

# نظام التحقق الذكي المدمج
class SmartDealValidator:
    """مُحقق ذكي للعروض مدمج"""
    
    def __init__(self):
        self.validated_deals = []
        self.rejected_deals = []
        
        # قواعد التحقق
        self.rules = {
            'min_price': 25,
            'max_discount': 85,
            'min_original_price': 60,
            'max_price_jump': 3.0
        }
        
        self.suspicious_keywords = [
            'fake', 'replica', 'copy', 'imitation', 
            'نسخة', 'تقليد', 'مقلد', 'مزيف'
        ]
    
    def validate_deal(self, item: dict, old_price: float, new_price: float, discount_percent: float) -> tuple:
        """تحقق من صحة العرض"""
        
        score = 100
        reasons = []
        
        # فحص السعر الأساسي
        if new_price < self.rules['min_price']:
            score -= 40
            reasons.append(f"سعر منخفض جداً ({new_price} EGP)")
        
        if old_price < self.rules['min_original_price']:
            score -= 25
            reasons.append(f"السعر الأصلي منخفض ({old_price} EGP)")
        
        # فحص نسبة الخصم
        if discount_percent > self.rules['max_discount']:
            score -= 50
            reasons.append(f"خصم مشكوك ({discount_percent:.1f}%)")
        
        # فحص القفزة السعرية
        if old_price / new_price > self.rules['max_price_jump']:
            score -= 35
            reasons.append("قفزة سعرية مشبوهة")
        
        # فحص اسم المنتج
        product_name = item.get('name', '').lower()
        for keyword in self.suspicious_keywords:
            if keyword in product_name:
                score -= 30
                reasons.append(f"اسم مشبوه: {keyword}")
        
        # فحص معقولية السعر للفئة
        section = item.get('section', '')
        if not self.is_price_reasonable(section, new_price):
            score -= 20
            reasons.append(f"سعر غير معقول لفئة {section}")
        
        # تحديد النتيجة
        if score >= 70:
            return True, f"✅ عرض موثوق ({score}/100)", score
        elif score >= 50:
            return True, f"⚠️ عرض مقبول ({score}/100)", score
        else:
            return False, f"❌ عرض مرفوض: {', '.join(reasons[:2])} ({score}/100)", score
    
    def is_price_reasonable(self, section: str, price: float) -> bool:
        """فحص معقولية السعر للفئة"""
        section_ranges = {
            'Electronics': (50, 50000),
            'Beauty': (20, 3000),
            'Fashion': (30, 8000),
            'Home & Kitchen': (25, 15000),
            'Automotive': (100, 30000),
            'Health & Household Products': (15, 2000),
            'Grocery': (5, 500),
            'Tools & Home Improvement': (50, 20000)
        }
        
        if section in section_ranges:
            min_price, max_price = section_ranges[section]
            return min_price <= price <= max_price
        
        return 20 <= price <= 50000

# إنشاء مُحقق العروض
deal_validator = SmartDealValidator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع التحقق الذكي"""
    
    # التحقق الذكي أولاً
    if smart_validation_enabled[0]:
        is_valid, reason, score = deal_validator.validate_deal(item, old_price, new_price, discount_percent)
        
        if not is_valid:
            print(f"🚫 تم رفض التنبيه: {item.get('name', '')[:40]}... - {reason}")
            deal_validator.rejected_deals.append({
                'name': item.get('name', ''),
                'reason': reason,
                'score': score,
                'timestamp': datetime.now().isoformat()
            })
            return
        
        # إضافة معلومات التحقق للعرض
        item['validation_info'] = reason
        item['trust_score'] = score
        deal_validator.validated_deals.append({
            'name': item.get('name', ''),
            'reason': reason,
            'score': score,
            'timestamp': datetime.now().isoformat()
        })
    
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
        alert_flag = item.get("alert_flag", "")
        
        # إضافة معلومات التحقق للرسالة
        validation_info = item.get('validation_info', '')
        trust_score = item.get('trust_score', 0)

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
        
        # إضافة معلومات الثقة للرسالة
        trust_row = f"\n🧠 <b>Trust:</b> {validation_info}" if validation_info else ""

        msg = f"""{alert_flag_row}{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Open Product</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{trust_row}
📊 <b>Price on Kanbkam:</b> <a href="{kanbkam_url}">View Chart</a>
"""

        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ View on Amazon", "url": url}],
                [{"text": "📊 View on Kanbkam", "url": kanbkam_url}]
            ]
        }
        reply_markup_json = json.dumps(reply_markup)

        sent_count = 0
        for user_id in users:
            try:
                if img_url:
                    response = requests.post(
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
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={
                            "chat_id": user_id,
                            "text": msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, timeout=15
                    )
                
                if response.status_code == 200:
                    sent_count += 1

            except Exception as e:
                print(f"❌ خطأ إرسال للمستخدم {user_id}: {e}")
        
        if sent_count > 0:
            print(f"✅ تم إرسال تنبيه ذكي لـ {sent_count} مستخدم - {validation_info}")

    except Exception as e:
        print("❌ Telegram Error:", e)

def load_db():
    """تحميل قاعدة البيانات"""
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
    """حفظ قاعدة البيانات"""
    try:
        # نسخة احتياطية
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
    """إضافة رسالة للسجل"""
    msg_no_links = re.sub(r'https?://\S+|www\.\S+', '', msg).strip()
    if not msg_no_links:
        return
    log_textbox.configure(state="normal")
    log_textbox.insert("end", f"{emoji} {msg_no_links}\n")
    log_textbox.see("end")
    log_textbox.configure(state="disabled")

def export_csv():
    """تصدير CSV"""
    with open("products_export.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price"])
        for asin, item in db.items():
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"]])
    log("Exported to CSV.", "📁")

def update_progress(val):
    """تحديث شريط التقدم"""
    progress_bar.set(val)

def get_discount_tag(discount_percent):
    """الحصول على تاج الخصم"""
    for level, icon, color in DISCOUNT_TAGS:
        if discount_percent >= level:
            return icon, color
    return "⚡", "#47ffd1"

def add_alert_data(item, old_price, new_price, discount_percent, drop_detected=False):
    """إضافة بيانات التنبيه مع التحقق الذكي"""
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

# دوال السكرابة المدمجة
def parse_egp_price(text):
    """استخراج السعر من النص"""
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

def extract_any_number(text):
    """استخراج أي رقم من النص"""
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=30):
    """سكرابة صفحة واحدة مع التحسينات"""
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-images'])
        context = await browser.new_context()
        page = await context.new_page()
        
        # تحسين URL للمنتجات الجديدة
        if auto_new_products_mode[0]:
            base_url = section_url.split('&page=')[0]
            if random.choice([True, False]):
                url = f"{base_url}&s=date-desc-rank&page={page_num}"
            else:
                random_page = random.randint(page_num, page_num + 30)
                url = section_url.format(random_page)
        else:
            url = section_url.format(page_num)
        
        if log_fn:
            mode = "[NEW MODE]" if auto_new_products_mode[0] else ""
            smart_mode = "[SMART FILTER]" if smart_validation_enabled[0] else ""
            log_fn(f"🌐 {mode}{smart_mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            if log_fn:
                log_fn(f"❌ Error loading page: {e}")
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        scraped_count = 0
        new_count = 0
        skipped_count = 0

        for item in items:
            try:
                asin = await item.get_attribute("data-asin")
                if not asin or asin.strip() == "":
                    continue

                # فلترة المنتجات الجديدة
                if auto_new_products_mode[0] and asin in existing_asins:
                    skipped_count += 1
                    continue

                # استخراج البيانات
                title_el = await item.query_selector('h2 span')
                name = await title_el.inner_text() if title_el else "?"

                img_el = await item.query_selector('img.s-image')
                img = await img_el.get_attribute("src") if img_el else ""

                anchors = await item.query_selector_all('a.a-link-normal')
                long_url = ""
                for a in anchors:
                    href = await a.get_attribute("href")
                    if href and ('/dp/' in href or '/-/en/' in href):
                        long_url = "https://www.amazon.eg" + href
                        break

                # استخراج السعر
                price = None
                price_el = await item.query_selector('.a-price .a-offscreen')
                if price_el:
                    price_txt = await price_el.inner_text()
                    price = parse_egp_price(price_txt)
                else:
                    price_txt = await item.inner_text()
                    price = extract_any_number(price_txt)
                price = float(price) if price else None

                # التحقق من التوفر
                not_avail_texts = ["غير متوفر", "غير متوفر حاليًا", "no featured offers available", "currently unavailable"]
                card_text = (await item.inner_text()).lower()
                if price is None or any(txt.lower() in card_text for txt in not_avail_texts):
                    continue

                # السعر المشطوب
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)

                # حساب نسبة الخصم
                discount_percent = None
                if strike_price and price and strike_price > price:
                    discount_percent = ((strike_price - price) / strike_price) * 100
                    is_super_drop = discount_percent > 90 or price < 20
                    flag = "⚠️ SUPER DROP" if is_super_drop else ""
                    
                    if discount_percent >= discount_threshold and discount_percent <= 98 and price >= 4:
                        if discount_alert_cb:
                            discount_alert_cb(
                                {
                                    "asin": asin,
                                    "name": name + (" " + flag if flag else ""),
                                    "url": long_url,
                                    "img": img,
                                    "section": section,
                                    "price": price,
                                    "strike_price": strike_price,
                                    "discount_percent": discount_percent,
                                    "drop_detected": False,
                                    "alert_flag": flag,
                                },
                                strike_price,
                                price,
                                discount_percent,
                                False
                            )

                # إضافة للقاعدة
                if asin not in db:
                    new_count += 1
                    db[asin] = {
                        "name": name,
                        "url": long_url,
                        "img": img,
                        "section": section,
                        "price": price,
                        "strike_price": strike_price,
                        "discount_percent": discount_percent,
                        "price_history": [],
                        "found_at": datetime.now().isoformat()
                    }
                    existing_asins.add(asin)
                else:
                    # تحديث البيانات
                    db[asin]["name"] = name
                    db[asin]["url"] = long_url
                    db[asin]["img"] = img
                    db[asin]["section"] = section
                    db[asin]["price"] = price
                    db[asin]["strike_price"] = strike_price
                    db[asin]["discount_percent"] = discount_percent

                # إضافة تاريخ السعر
                now = datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M")
                last_history = db[asin]["price_history"][-1] if db[asin]["price_history"] else None
                is_new_history = (
                    not last_history or
                    last_history.get("date") != date_str or
                    last_history.get("price") != price
                )
                if is_new_history:
                    db[asin]["price_history"].append({
                        "date": date_str,
                        "time": time_str,
                        "price": price
                    })

                scraped_count += 1

            except Exception as e:
                if log_fn:
                    log_fn(f"⚠️ Error parsing item: {e}")

        await browser.close()
        
        # تقرير محسن
        if log_fn:
            if auto_new_products_mode[0]:
                log_fn(f"[Page {page_num}] ✅ {new_count} NEW, {skipped_count} skipped")
            else:
                log_fn(f"[Page {page_num}] ✅ Scraped {scraped_count} products")
        
        return scraped_count

async def scrape_section(section, section_url, start_page, end_page, db, log_fn=None, progress_fn=None, 
                        stop_flag=None, discount_alert_cb=None, concurrency=10, max_empty_retries=3, 
                        discount_threshold=30):
    """سكرابة قسم كامل"""
    pages = list(range(start_page, end_page + 1))
    semaphore = asyncio.Semaphore(concurrency)

    async def scrape_with_limit(page_num):
        async with semaphore:
            if stop_flag and stop_flag.get("stop"):
                return "stopped"
            count = await scrape_single_page(
                section, section_url, page_num, db, log_fn=log_fn,
                discount_alert_cb=discount_alert_cb, discount_threshold=discount_threshold
            )
            if progress_fn:
                progress_fn(page_num)
            return (page_num, count)

    tasks = [scrape_with_limit(page_num) for page_num in pages]
    for fut in asyncio.as_completed(tasks):
        res = await fut
        if res == "stopped":
            if log_fn:
                log_fn("⛔️ Stopped by user.")
            return
        page_num, scraped_count = res
        if log_fn:
            log_fn(f"[Page {page_num}] ✅ Scraped {scraped_count} products")

# شاشة المنتجات (نفس الأصلية)
class AlertsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Alerts / Products")
        self.configure(bg="#232d3a")
        self.minsize(900, 450)
        self.geometry("1300x730")
        self.page = 0
        self._last_cols = None
        self._img_cache = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

        self.outer_frame = ctk.CTkFrame(self, fg_color="#232d3a")
        self.outer_frame.pack(expand=True, fill="both", padx=16, pady=16)
        self.outer_frame.grid_rowconfigure(0, weight=1)
        self.outer_frame.grid_columnconfigure(0, weight=1)

        self.main_canvas = ctk.CTkCanvas(self.outer_frame, bg="#232d3a", highlightthickness=0)
        self.main_canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(self.outer_frame, orientation="vertical", command=self.main_canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.cards_frame = ctk.CTkFrame(self.main_canvas, fg_color="#232d3a")
        self.main_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")

        pag_frame = ctk.CTkFrame(self, fg_color="#232d3a")
        pag_frame.pack(side="bottom", fill="x", pady=(0,16))
        self.prev_btn = ctk.CTkButton(pag_frame, text="⬅ Prev", font=("Arial", 17, "bold"),
                                      command=self.prev_page, width=120, fg_color="#54fac8", text_color="#232d3a")
        self.prev_btn.pack(side="left", padx=12, pady=5)
        self.page_lbl = ctk.CTkLabel(pag_frame, text="", font=("Arial", 18, "bold"), text_color="#6cfbc8")
        self.page_lbl.pack(side="left", padx=6)
        self.next_btn = ctk.CTkButton(pag_frame, text="Next ➡", font=("Arial", 17, "bold"),
                                      command=self.next_page, width=120, fg_color="#54fac8", text_color="#232d3a")
        self.next_btn.pack(side="left", padx=12, pady=5)

        self.bind("<Configure>", self._on_resize)
        self.after(100, self.refresh)

    def _on_resize(self, event=None):
        cols = self.get_dynamic_cols()
        if cols != self._last_cols:
            self._last_cols = cols
            self.after(10, self.refresh)
        self.cards_frame.update_idletasks()
        self.main_canvas.config(scrollregion=self.main_canvas.bbox("all"))

    def get_dynamic_cols(self):
        w = self.winfo_width()
        if w < 700:
            return 1
        elif w < 1050:
            return 2
        elif w < 1500:
            return 3
        else:
            return 4

    def render_alert_card(self, data, idx_in_page, cols, card_size):
        item = data["item"]
        old_price = data["old_price"]
        new_price = data["new_price"]
        discount_percent = data["discount_percent"]
        drop_detected = data["drop_detected"]

        # معلومات التحقق الذكي
        validation_info = item.get('validation_info', '')
        trust_score = item.get('trust_score', 0)

        if drop_detected:
            icon, color = DROP_TAG
            label_title = "Sudden Price Drop!"
        else:
            icon, color = get_discount_tag(discount_percent)
            label_title = f"{icon}  {discount_percent:.1f}% OFF"

        # تغيير لون الإطار حسب مستوى الثقة
        if trust_score >= 80:
            border_color = "#00ff00"  # أخضر للموثوق
        elif trust_score >= 60:
            border_color = "#ffaa00"  # برتقالي للمتوسط
        else:
            border_color = color

        card = ctk.CTkFrame(
            self.cards_frame,
            fg_color="#222a34",
            border_width=3,
            border_color=border_color,
            corner_radius=18,
            width=card_size,
            height=card_size,
        )
        row, col = divmod(idx_in_page, cols)
        card.grid(row=row, column=col, padx=18, pady=16, sticky="nsew")

        img_side = min(110, card_size-30)
        img_frame = ctk.CTkFrame(card, fg_color="transparent", width=img_side, height=img_side)
        img_frame.pack(side="left", padx=(16, 8), pady=16)
        img_frame.pack_propagate(False)

        img_label = ctk.CTkLabel(img_frame, text="Loading...", font=("Arial", 10), width=img_side, height=img_side)
        img_label.pack(expand=True, fill="both")

        def load_img():
            url = item.get("img")
            if not url:
                img_label.after(0, lambda: img_label.configure(text="No Image", image=""))
                return
            if url in self._img_cache:
                ctk_img = self._img_cache[url]
                img_label.after(0, lambda: (img_label.configure(image=ctk_img, text=""), setattr(img_label, "image", ctk_img)))
                return
            try:
                r = requests.get(url, timeout=6)
                pil_img = Image.open(BytesIO(r.content)).resize((img_side, img_side))
                ctk_img = ctk.CTkImage(dark_image=pil_img, size=(img_side, img_side))
                self._img_cache[url] = ctk_img
                img_label.after(0, lambda: (img_label.configure(image=ctk_img, text=""), setattr(img_label, "image", ctk_img)))
            except Exception:
                img_label.after(0, lambda: img_label.configure(text="No Image", image=""))
        self._executor.submit(load_img)

        right_frame = ctk.CTkFrame(card, fg_color="transparent", width=card_size-img_side-40)
        right_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        right_frame.pack_propagate(False)

        title = item["name"][:58] + ("..." if len(item["name"]) > 58 else "")
        title_label = ctk.CTkLabel(
            right_frame, text=title,
            font=("Arial Black", 16, "bold"), text_color="#41ffe0",
            anchor="w", wraplength=card_size-img_side-60, justify="left"
        )
        title_label.pack(pady=(4, 2), anchor="w")

        # عرض معلومات التحقق
        if validation_info:
            validation_label = ctk.CTkLabel(
                right_frame, text=validation_info[:30],
                font=("Arial", 11, "bold"), text_color=border_color,
                anchor="w"
            )
            validation_label.pack(pady=(1, 2), anchor="w")

        price_row = ctk.CTkFrame(right_frame, fg_color="transparent")
        price_row.pack(anchor="w", pady=(2, 0), fill="x")
        old_label = ctk.CTkLabel(
            price_row,
            text=f"🔻 {int(old_price):,} EGP",
            font=("Arial", 16, "bold"),
            text_color="#fe8989"
        )
        old_label.pack(side="left", padx=(0, 9))
        new_label = ctk.CTkLabel(
            price_row,
            text=f"💰 {int(new_price):,} EGP",
            font=("Arial", 18, "bold"),
            text_color="#b9ffa3"
        )
        new_label.pack(side="left", padx=(0, 8))

        disc_label = ctk.CTkLabel(
            right_frame,
            text=label_title,
            font=("Arial Black", 17, "bold"),
            text_color=color,
            anchor="w"
        )
        disc_label.pack(pady=(2, 5), anchor="w")

        url = item.get("url")
        btn = ctk.CTkButton(
            right_frame,
            text="Open Product 🔗",
            fg_color=color,
            hover_color="#444",
            text_color="#232d3a",
            font=("Arial", 15, "bold"),
            width=140, height=36,
            command=lambda: webbrowser.open(url)
        )
        btn.pack(anchor="e", pady=(11, 6), padx=10, side="right")

    def refresh(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()
        cols = self.get_dynamic_cols()
        card_size = int((self.winfo_width() - (cols+1)*40) / cols) if cols > 0 else 340
        PAGE_SIZE = cols * 3
        page = self.page
        total_pages = max(1, ((len(alerts_data) - 1) // PAGE_SIZE) + 1)
        self.page = max(0, min(page, total_pages - 1))
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_data = alerts_data[start:end]

        if not page_data:
            empty_lbl = ctk.CTkLabel(self.cards_frame, text="No alerts to show.", font=("Arial", 18), text_color="#54fac8")
            empty_lbl.pack(pady=60)
        else:
            for idx, alert in enumerate(page_data):
                self.render_alert_card(alert, idx, cols, card_size)

        self.page_lbl.configure(text=f"Page {self.page+1} of {total_pages}")
        self.prev_btn.configure(state="normal" if self.page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.page < total_pages-1 else "disabled")
        self.cards_frame.update_idletasks()
        self.main_canvas.config(scrollregion=self.main_canvas.bbox("all"))

    def next_page(self):
        self.page += 1
        self.refresh()

    def prev_page(self):
        self.page -= 1
        self.refresh()

def open_alerts_window():
    AlertsWindow(root)

def scraper_func(section, pages, all_pages):
    """دالة السكرابر الرئيسية"""
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    notified_asins.clear()
    alerts_data.clear()
    
    def alert_callback(item, old_price, new_price, discount_percent, drop_detected=False):
        add_alert_data(item, old_price, new_price, discount_percent, drop_detected=drop_detected)
    
    if all_pages:
        pages = 500
    
    if section == "All Sections":
        for sec in list(CATEGORIES.keys()):
            if stop_flag.get("stop"):
                break
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
    """بدء السكرابة"""
    if running[0]:
        log("Already running.", "⚠️")
        return
    section = section_combo.get()
    all_pages = all_pages_chk.get()
    pages = int(pages_entry.get()) if not all_pages else 9999
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    # رسائل الحالة
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    smart_mode = "ON" if smart_validation_enabled[0] else "OFF"
    log(f"🚀 Starting - Auto New: {auto_mode}, Smart Filter: {smart_mode}")
    
    global scrape_thread
    scrape_thread = threading.Thread(target=scraper_func, args=(section, pages, all_pages), daemon=True)
    scrape_thread.start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    """عرض الإحصائيات مع معلومات التحقق"""
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات التحقق الذكي
    if smart_validation_enabled[0]:
        validated = len(deal_validator.validated_deals)
        rejected = len(deal_validator.rejected_deals)
        total_checked = validated + rejected
        
        if total_checked > 0:
            success_rate = (validated / total_checked) * 100
            log(f"🧠 Smart Validation:")
            log(f"   ✅ Validated: {validated}")
            log(f"   ❌ Rejected: {rejected}")
            log(f"   📈 Success Rate: {success_rate:.1f}%")

def show_validation_report():
    """عرض تقرير التحقق"""
    if smart_validation_enabled[0]:
        validated = len(deal_validator.validated_deals)
        rejected = len(deal_validator.rejected_deals)
        
        log("📊 Validation Report:")
        log(f"   📱 Messages sent: {validated}")
        log(f"   🚫 Messages blocked: {rejected}")
        log(f"   💾 Report saved to file")
        
        # حفظ التقرير
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'validated_deals': deal_validator.validated_deals,
            'rejected_deals': deal_validator.rejected_deals,
            'summary': {
                'total_validated': validated,
                'total_rejected': rejected,
                'success_rate': (validated / max(validated + rejected, 1)) * 100
            }
        }
        
        with open(f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

def toggle_smart_validation():
    """تفعيل/إلغاء التحقق الذكي"""
    smart_validation_enabled[0] = smart_validation_chk.get()
    status = "ON" if smart_validation_enabled[0] else "OFF"
    log(f"🧠 Smart Validation: {status}")

def toggle_auto_new_mode():
    """تفعيل/إلغاء وضع المنتجات الجديدة"""
    auto_new_products_mode[0] = auto_new_chk.get()
    status = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🆕 Auto New Products: {status}")

def resume_scraping():
    load_db()
    log("📦 Database loaded.")
    show_stats()

def exit_app():
    stop_flag["stop"] = True
    save_db()
    root.destroy()

def clear_log():
    log_textbox.configure(state="normal")
    log_textbox.delete("1.0", "end")
    log_textbox.configure(state="disabled")

# ==== MAIN ROOT ====
root = ctk.CTk()
root.title("LAQTA - Smart Deal Hunter")
root.geometry("1400x1000")
root.minsize(1100, 750)
root.rowconfigure(3, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - SMART DEALS", font=("SST Arabic Medium", 65), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=1, column=0, padx=10, pady=7, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7,8), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=200, font=("Arial", 16), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=6, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=80, font=("Arial", 16), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "10")
pages_entry.grid(row=0, column=1, padx=6, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 14), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=6, pady=8, sticky="ew")

all_pages_chk = ctk.CTkCheckBox(controls_frame, text="All Pages", font=("Arial", 14), text_color="#59ff9d")
all_pages_chk.grid(row=0, column=3, padx=6, pady=8, sticky="ew")

# المنتجات الجديدة تلقائياً
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 Auto New", font=("Arial", 14, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=4, padx=6, pady=8, sticky="ew")
auto_new_chk.select()

# التحقق الذكي
smart_validation_chk = ctk.CTkCheckBox(controls_frame, text="🧠 Smart Filter", font=("Arial", 14, "bold"), 
                                      text_color="#00aaff", command=toggle_smart_validation)
smart_validation_chk.grid(row=0, column=5, padx=6, pady=8, sticky="ew")
smart_validation_chk.select()

def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]

telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="📱 Telegram", font=("Arial", 14), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=6, padx=6, pady=8, sticky="ew")
telegram_checkbox.select()

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

min_discount_slider = ctk.CTkSlider(
    controls_frame, from_=1, to=99, number_of_steps=98, width=100,
    command=set_min_discount, progress_color="#12dafb"
)
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=7, padx=6, pady=8, sticky="ew")

min_discount_label = ctk.CTkLabel(
    controls_frame, text=f"Min: {ALERT_DISCOUNT}%", font=("Arial", 12), text_color="#59ff9d"
)
min_discount_label.grid(row=0, column=8, padx=6, pady=8, sticky="ew")

open_alerts_btn = ctk.CTkButton(controls_frame, text="Alerts 📢", font=("Arial", 14, "bold"),
    command=open_alerts_window, fg_color="#59ff9d", hover_color="#13e6a7", text_color="#232d3a", width=100, height=35)
open_alerts_btn.grid(row=0, column=9, padx=6, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=22, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=2, column=0, padx=10, pady=7, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 14), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=220)
log_textbox.grid(row=3, column=0, padx=15, pady=(0, 12), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)

btn_w, btn_h = 150, 45
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="Start 🚀", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
start_btn.grid(row=0, column=0, padx=6, pady=8, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="Stop ✋", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#54fac8", text_color="#111927")
stop_btn.grid(row=0, column=1, padx=6, pady=8, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="Resume 🔁", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#12dafb", text_color="#111927")
resume_btn.grid(row=0, column=2, padx=6, pady=8, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="Export 📁", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#59ff9d", text_color="#111927")
export_btn.grid(row=0, column=3, padx=6, pady=8, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="Stats 📊", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#54fac8", text_color="#111927")
stats_btn.grid(row=0, column=4, padx=6, pady=8, sticky="ew")

report_btn = ctk.CTkButton(buttons_frame, text="Report 📋", command=show_validation_report, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ff6666", hover_color="#ff8888", text_color="#ffffff")
report_btn.grid(row=0, column=5, padx=6, pady=8, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="Clear 🧹", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=6, padx=6, pady=8, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=350, height=50,
    font=("Arial Black", 20), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=5, column=0, pady=(10, 14))

load_db()

# رسائل ترحيب
log("🎯 LAQTA Smart Deal Hunter started!", "🚀")
log("🆕 Auto New Products: ON - سيتم البحث عن المنتجات الجديدة تلقائياً", "✨")
log("🧠 Smart Filter: ON - سيتم فلترة العروض الوهمية", "💡")
log("📱 Expected: Much fewer but REAL deals!", "🏆")

root.mainloop()
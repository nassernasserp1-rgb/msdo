#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
الواجهة الأصلية المُصلحة مع ميزة المنتجات الجديدة فقط
"""

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime
from playwright.async_api import async_playwright
import sqlite3
import random
import requests

# إعداد الواجهة (نفس الأصلية)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# الفئات (نفس الأصلية)
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Grocery': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18020637031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Health & Household Products': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021875031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Tools & Home Improvement': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021990031%2Cp_98%3A21909049031&dc&page={}&language=en",
}

# متغيرات عامة (نفس الأصلية)
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
ALERT_DISCOUNT = 30
alerts_data = []
notified_asins = set()

# إضافة متغير للمنتجات الجديدة فقط
new_products_only_mode = [False]
existing_asins = set()

def load_db():
    """تحميل قاعدة البيانات (نفس الأصلية مع تحسين)"""
    global db, existing_asins
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
            
            # تحميل ASINs الموجودة للفلترة السريعة
            existing_asins = set(db.keys())
            print(f"📦 تم تحميل {len(db):,} منتج موجود")
        except Exception as e:
            print(f"❌ خطأ في تحميل قاعدة البيانات: {e}")
            db = {}
            existing_asins = set()
    else:
        db = {}
        existing_asins = set()

def save_db():
    """حفظ قاعدة البيانات (نفس الأصلية مع تحسين)"""
    try:
        # حفظ نسخة احتياطية
        if os.path.exists(DB_FILE):
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.rename(DB_FILE, backup_name)
            print(f"💾 تم إنشاء نسخة احتياطية: {backup_name}")
        
        # حفظ البيانات الجديدة
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        
        print(f"💾 تم حفظ {len(db):,} منتج في {DB_FILE}")
        
    except Exception as e:
        print(f"❌ خطأ في حفظ قاعدة البيانات: {e}")

def send_telegram_alert_fixed(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مُصلح"""
    try:
        # البحث عن ملف الإعدادات
        config_files = ["telegram_config.json"]
        config = None
        
        for config_file in config_files:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                break
        
        if not config:
            print("❌ ملف telegram_config.json غير موجود")
            return False
        
        bot_token = config.get("bot_token")
        users = config.get("users", [])
        
        if not bot_token or not users:
            print("❌ إعدادات التليجرام غير مكتملة")
            return False

        # تحضير الرسالة (مبسطة)
        product_name = item.get('name', 'منتج غير محدد')[:80]
        url = item.get('url', '')
        section = item.get('section', 'غير محدد')
        
        if drop_detected:
            headline = "🚨 انخفاض سعر مفاجئ!"
        elif discount_percent >= 50:
            headline = "🔥 خصم خيالي!"
        elif discount_percent >= 30:
            headline = "🎉 خصم ممتاز!"
        else:
            headline = "💸 خصم جديد!"

        price_old = f"{int(old_price):,} جنيه" if old_price else ""
        price_new = f"{int(new_price):,} جنيه" if new_price else ""
        
        message = f"""{headline}

{product_name}

💰 السعر: {price_old} → {price_new}
⚡ الخصم: {discount_percent:.1f}%
📦 القسم: {section}
🕐 {datetime.now().strftime('%H:%M:%S')}

🔗 رابط المنتج: {url}"""

        # إرسال لجميع المستخدمين
        success_count = 0
        for user_id in users:
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={
                        "chat_id": user_id,
                        "text": message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False
                    }, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"✅ تم إرسال تنبيه للمستخدم {user_id}")
                else:
                    print(f"❌ فشل الإرسال للمستخدم {user_id}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ خطأ في إرسال رسالة للمستخدم {user_id}: {e}")

        return success_count > 0

    except Exception as e:
        print(f"❌ خطأ في التليجرام: {e}")
        return False

def log(msg, emoji=""):
    """إضافة رسالة للسجل (نفس الأصلية)"""
    msg_no_links = msg.replace('https://', '').replace('www.', '')
    if not msg_no_links.strip():
        return
    log_textbox.configure(state="normal")
    log_textbox.insert("end", f"{emoji} {msg_no_links}\n")
    log_textbox.see("end")
    log_textbox.configure(state="disabled")

def update_progress(val):
    """تحديث شريط التقدم (نفس الأصلية)"""
    progress_bar.set(val)

def add_alert_data(item, old_price, new_price, discount_percent, drop_detected=False):
    """إضافة بيانات التنبيه (مُصلحة)"""
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
    
    # إرسال على تليجرام مع الدالة المُصلحة
    if telegram_alerts_enabled[0]:
        try:
            threading.Thread(
                target=send_telegram_alert_fixed, 
                args=(item, old_price, new_price, discount_percent, drop_detected), 
                daemon=True
            ).start()
            print(f"📱 تم إرسال تنبيه تليجرام للمنتج: {item.get('name', 'Unknown')[:30]}...")
        except Exception as e:
            print(f"❌ خطأ في إرسال التليجرام: {e}")

async def scrape_single_page_improved(section, section_url, page_num, db, log_fn=None, 
                                     discount_alert_cb=None, discount_threshold=30):
    """سكرابة صفحة واحدة مُحسنة مع فلترة المنتجات الجديدة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-images'
        ])
        context = await browser.new_context()
        page = await context.new_page()
        
        # تحديد URL مع استراتيجية ذكية
        if new_products_only_mode[0]:
            # إضافة فلتر للأحدث إذا كان في وضع المنتجات الجديدة
            base_url = section_url.split('&page=')[0]
            url = f"{base_url}&s=date-desc-rank&page={page_num}"
        else:
            url = section_url.format(page_num)
        
        if log_fn:
            mode = "NEW ONLY" if new_products_only_mode[0] else "ALL"
            log_fn(f"🌐 [{mode}] Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            if log_fn:
                log_fn(f"❌ Error loading page: {e}")
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        scraped_count = 0
        new_products_count = 0

        for item in items:
            try:
                asin = await item.get_attribute("data-asin")
                if not asin or asin.strip() == "":
                    continue

                # فلترة المنتجات الجديدة إذا كان الوضع مفعل
                if new_products_only_mode[0] and asin in existing_asins:
                    continue  # تخطي المنتجات الموجودة

                # استخراج البيانات (نفس الطريقة الأصلية)
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
                    import re
                    m = re.search(r'(\d[\d,\.]*)', price_txt.replace(",", ""))
                    price = float(m.group(1)) if m else None

                if price is None:
                    continue

                # السعر المشطوب
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    import re
                    m = re.search(r'(\d[\d,\.]*)', strike_txt.replace(",", ""))
                    strike_price = float(m.group(1)) if m else None

                # حساب نسبة الخصم
                discount_percent = None
                if strike_price and price and strike_price > price:
                    discount_percent = ((strike_price - price) / strike_price) * 100

                # إنشاء بيانات المنتج
                product_data = {
                    "asin": asin,
                    "name": name,
                    "url": long_url,
                    "img": img,
                    "section": section,
                    "price": price,
                    "strike_price": strike_price,
                    "discount_percent": discount_percent,
                    "found_at": datetime.now().isoformat()
                }

                # إضافة للقاعدة
                if asin not in db:
                    new_products_count += 1
                    if log_fn and new_products_only_mode[0]:
                        log_fn(f"✨ NEW: {name[:40]}... - {price} EGP")

                db[asin] = product_data
                existing_asins.add(asin)  # إضافة للمجموعة الموجودة

                # التحقق من التنبيهات
                if (discount_percent and discount_percent >= discount_threshold and 
                    discount_percent <= 98 and price >= 4):
                    if discount_alert_cb:
                        discount_alert_cb(
                            product_data,
                            strike_price,
                            price,
                            discount_percent,
                            False
                        )

                scraped_count += 1

            except Exception as e:
                if log_fn:
                    log_fn(f"⚠️ Error parsing item: {e}")

        await browser.close()
        
        if log_fn:
            if new_products_only_mode[0]:
                log_fn(f"📊 Page {page_num}: {new_products_count} NEW products (skipped {scraped_count - new_products_count} existing)")
            else:
                log_fn(f"📊 Page {page_num}: {scraped_count} products total")
        
        return scraped_count

async def scrape_section_improved(section, section_url, start_page, end_page, db,
                                 log_fn=None, progress_fn=None, stop_flag=None, 
                                 discount_alert_cb=None, discount_threshold=30, concurrency=5):
    """سكرابة قسم مُحسنة (مبسطة من الأصلية)"""
    
    pages = list(range(start_page, end_page + 1))
    
    # إذا كان في وضع المنتجات الجديدة، خلط الصفحات للتنويع
    if new_products_only_mode[0]:
        random.shuffle(pages)
        # إضافة صفحات عشوائية من مجال أوسع
        extra_pages = random.sample(range(end_page + 1, end_page + 50), min(20, 50))
        pages.extend(extra_pages)
    
    semaphore = asyncio.Semaphore(concurrency)
    
    async def scrape_with_limit(page_num):
        async with semaphore:
            if stop_flag and stop_flag.get("stop"):
                return "stopped"
            
            count = await scrape_single_page_improved(
                section, section_url, page_num, db, log_fn=log_fn,
                discount_alert_cb=discount_alert_cb, discount_threshold=discount_threshold
            )
            
            if progress_fn:
                progress_fn(page_num)
            return (page_num, count)

    # تنفيذ المهام
    tasks = [scrape_with_limit(page_num) for page_num in pages]
    total_scraped = 0
    
    for fut in asyncio.as_completed(tasks):
        res = await fut
        if res == "stopped":
            if log_fn:
                log_fn("⛔️ Stopped by user.")
            return
        
        page_num, scraped_count = res
        total_scraped += scraped_count
        
        if log_fn:
            log_fn(f"[Page {page_num}] ✅ {scraped_count} products")

def scraper_func(section, pages, all_pages):
    """دالة السكرابر الرئيسية (مُحسنة)"""
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    notified_asins.clear()
    alerts_data.clear()
    
    def alert_callback(item, old_price, new_price, discount_percent, drop_detected=False):
        add_alert_data(item, old_price, new_price, discount_percent, drop_detected=drop_detected)
    
    if all_pages:
        pages = 200  # حد معقول
    
    if section == "All Sections":
        for sec in list(CATEGORIES.keys()):
            if stop_flag.get("stop"):
                break
            log(f"Scraping section: {sec}", "🟢")
            section_url = CATEGORIES[sec]
            loop.run_until_complete(scrape_section_improved(
                sec, section_url, 1, pages, db,
                log_fn=lambda m: log(m, "🟢"),
                progress_fn=lambda pn: update_progress(pn / pages),
                stop_flag=stop_flag,
                discount_alert_cb=alert_callback,
                discount_threshold=ALERT_DISCOUNT,
                concurrency=8
            ))
    else:
        section_url = CATEGORIES[section]
        loop.run_until_complete(scrape_section_improved(
            section, section_url, 1, pages, db,
            log_fn=lambda m: log(m, "🟢"),
            progress_fn=lambda pn: update_progress(pn / pages),
            stop_flag=stop_flag,
            discount_alert_cb=alert_callback,
            discount_threshold=ALERT_DISCOUNT,
            concurrency=8
        ))
    
    save_db()
    log("✅ Done.")
    running[0] = False

def start_scraping():
    """بدء السكرابة (نفس الأصلية)"""
    if running[0]:
        log("Already running.", "⚠️")
        return
    section = section_combo.get()
    all_pages = all_pages_chk.get()
    pages = int(pages_entry.get()) if not all_pages else 200
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    mode = "NEW PRODUCTS ONLY" if new_products_only_mode[0] else "ALL PRODUCTS"
    log(f"Starting scraping - Mode: {mode}", "🚀")
    
    global scrape_thread
    scrape_thread = threading.Thread(target=scraper_func, args=(section, pages, all_pages), daemon=True)
    scrape_thread.start()

def stop_scraping():
    """إيقاف السكرابة (نفس الأصلية)"""
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    """عرض الإحصائيات (مُحسنة)"""
    total_products = len(db)
    log(f"🔢 Total Products: {total_products:,}")
    
    # إحصائيات إضافية
    if new_products_only_mode[0]:
        new_today = sum(1 for item in db.values() 
                       if item.get('found_at', '').startswith(datetime.now().strftime('%Y-%m-%d')))
        log(f"✨ New Today: {new_today:,}")
    
    # إحصائيات الأقسام
    sections = {}
    for item in db.values():
        section = item.get('section', 'Unknown')
        sections[section] = sections.get(section, 0) + 1
    
    log("📂 Sections:")
    for section, count in sorted(sections.items(), key=lambda x: x[1], reverse=True)[:5]:
        log(f"   {section}: {count:,}")

def toggle_new_products_mode():
    """تفعيل/إلغاء وضع المنتجات الجديدة فقط"""
    new_products_only_mode[0] = new_products_only_chk.get()
    mode = "ENABLED" if new_products_only_mode[0] else "DISABLED"
    log(f"🆕 New Products Only Mode: {mode}")

def test_telegram():
    """اختبار التليجرام"""
    def test_thread():
        test_item = {
            "name": "🧪 اختبار LAQTA",
            "url": "https://amazon.eg/test",
            "section": "اختبار",
            "asin": "TEST123"
        }
        
        log("🧪 Testing Telegram...")
        success = send_telegram_alert_fixed(test_item, 100, 70, 30.0, False)
        
        if success:
            log("✅ Telegram test successful!")
        else:
            log("❌ Telegram test failed!")
    
    threading.Thread(target=test_thread, daemon=True).start()

def resume_scraping():
    """استئناف السكرابة (نفس الأصلية)"""
    load_db()
    log("📦 Database loaded.")
    show_stats()

def exit_app():
    """إغلاق التطبيق (نفس الأصلية)"""
    stop_flag["stop"] = True
    save_db()
    root.destroy()

def clear_log():
    """مسح السجل (نفس الأصلية)"""
    log_textbox.configure(state="normal")
    log_textbox.delete("1.0", "end")
    log_textbox.configure(state="disabled")

# ==== MAIN ROOT (نفس الأصلية مع إضافات) ====
root = ctk.CTk()
root.title("LAQTA - Simple & Fixed")
root.geometry("1400x980")
root.minsize(1100, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - SIMPLE & FIXED", font=("Arial", 60, "bold"), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(18, 5), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=1, column=0, padx=10, pady=7, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=200, font=("Arial", 16), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=100, font=("Arial", 16), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "20")
pages_entry.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 16), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

all_pages_chk = ctk.CTkCheckBox(controls_frame, text="All Pages", font=("Arial", 15), text_color="#59ff9d")
all_pages_chk.grid(row=0, column=3, padx=10, pady=8, sticky="ew")

# إضافة checkbox للمنتجات الجديدة فقط
new_products_only_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 15, "bold"), 
                                       text_color="#ff6666", command=toggle_new_products_mode)
new_products_only_chk.grid(row=0, column=4, padx=10, pady=8, sticky="ew")

# checkbox التليجرام (نفس الأصلية)
def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]
    
telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="📱 Telegram", font=("Arial", 15), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=5, padx=10, pady=8, sticky="ew")
telegram_checkbox.select()

# سلايدر الخصم (مبسط)
min_discount_slider = ctk.CTkSlider(controls_frame, from_=1, to=99, number_of_steps=98, width=120,
    progress_color="#12dafb")
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=6, padx=10, pady=8, sticky="ew")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

min_discount_slider.configure(command=set_min_discount)
min_discount_label = ctk.CTkLabel(controls_frame, text=f"Min: {ALERT_DISCOUNT}%", font=("Arial", 14), text_color="#59ff9d")
min_discount_label.grid(row=0, column=7, padx=6, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=22, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=2, column=0, padx=10, pady=7, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 14), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=200)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 12), sticky="nsew")
log_textbox.configure(state="disabled")

# أزرار التحكم (نفس الأصلية مع إضافات)
buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)

btn_w, btn_h = 160, 48
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="Start 🚀", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
start_btn.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="Stop ✋", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#54fac8", text_color="#111927")
stop_btn.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="Resume 🔁", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#12dafb", text_color="#111927")
resume_btn.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="Stats 📊", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#59ff9d", hover_color="#54fac8", text_color="#111927")
stats_btn.grid(row=0, column=3, padx=8, pady=8, sticky="ew")

# زر اختبار التليجرام (جديد)
test_telegram_btn = ctk.CTkButton(buttons_frame, text="Test 📱", command=test_telegram, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ff6666", hover_color="#ff8888", text_color="#ffffff")
test_telegram_btn.grid(row=0, column=4, padx=8, pady=8, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="Clear 🧹", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=5, padx=8, pady=8, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=300, height=50,
    font=("Arial", 20, "bold"), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(10, 14))

# تحميل قاعدة البيانات عند البدء
load_db()

# رسالة ترحيب
log("🎯 LAQTA Simple & Fixed started!")
log("🆕 NEW: Enable 'New Only' to find new products faster!")
log("📱 Click 'Test Telegram' to check alerts!")

root.mainloop()
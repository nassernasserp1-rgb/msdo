#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النظام الصادق والحقيقي
بدون مقارنات وهمية - نتائج حقيقية فقط
"""

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime
import re
from PIL import Image
import requests
from io import BytesIO
import webbrowser
import concurrent.futures
from playwright.async_api import async_playwright
import statistics
import random
import time

# جميع الفئات الأصلية
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Sports & Outdoors': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018038031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Baby Products': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017908031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Books': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017915031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Health & Personal Care': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017995031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Toys & Games': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018059031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Office Products': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018024031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Pet Supplies': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018031031%2Cp_98%3A21909049031&dc&page={}&language=en"
}

# إعداد الواجهة الأصلية
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# متغيرات عامة
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
honest_mode_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام صادق بدون مقارنات وهمية
class HonestDealAnalyzer:
    """محلل صادق للعروض - بدون مقارنات وهمية"""
    
    def __init__(self):
        self.stats = {
            'total_deals': 0,
            'high_discount_deals': 0,
            'medium_discount_deals': 0,
            'low_discount_deals': 0,
            'price_drop_deals': 0,
            'sent_alerts': 0,
            'rejected_deals': 0
        }
    
    def analyze_deal_honestly(self, item: dict, old_price: float, new_price: float, discount_percent: float) -> dict:
        """تحليل صادق للعرض بدون مقارنات وهمية"""
        
        result = {
            'is_worth_sending': False,
            'confidence': 0,
            'reason': '',
            'category': '',
            'analysis_method': 'honest_analysis'
        }
        
        # تحليل صادق بناءً على نسبة الخصم فقط
        if discount_percent >= 50:
            result['confidence'] = 90
            result['reason'] = f"🔥 خصم ضخم {discount_percent:.0f}%!"
            result['category'] = 'خصم ضخم'
            result['is_worth_sending'] = True
            self.stats['high_discount_deals'] += 1
            
        elif discount_percent >= 35:
            result['confidence'] = 80
            result['reason'] = f"✅ خصم كبير {discount_percent:.0f}%"
            result['category'] = 'خصم كبير'
            result['is_worth_sending'] = True
            self.stats['high_discount_deals'] += 1
            
        elif discount_percent >= 25:
            result['confidence'] = 70
            result['reason'] = f"⚡ خصم جيد {discount_percent:.0f}%"
            result['category'] = 'خصم جيد'
            result['is_worth_sending'] = True
            self.stats['medium_discount_deals'] += 1
            
        elif discount_percent >= 15:
            result['confidence'] = 60
            result['reason'] = f"💸 خصم متوسط {discount_percent:.0f}%"
            result['category'] = 'خصم متوسط'
            result['is_worth_sending'] = True
            self.stats['medium_discount_deals'] += 1
            
        elif discount_percent >= 10:
            result['confidence'] = 50
            result['reason'] = f"⚠️ خصم بسيط {discount_percent:.0f}%"
            result['category'] = 'خصم بسيط'
            result['is_worth_sending'] = True
            self.stats['low_discount_deals'] += 1
            
        else:
            result['confidence'] = 30
            result['reason'] = f"❌ خصم ضعيف {discount_percent:.0f}%"
            result['category'] = 'خصم ضعيف'
            result['is_worth_sending'] = False
            self.stats['rejected_deals'] += 1
        
        # تحليل إضافي للسعر
        price_analysis = ""
        if new_price <= 50:
            price_analysis = " (منتج اقتصادي)"
        elif new_price <= 200:
            price_analysis = " (سعر متوسط)"
        elif new_price <= 1000:
            price_analysis = " (سعر مرتفع)"
        else:
            price_analysis = " (منتج غالي)"
        
        result['reason'] += price_analysis
        
        # تحليل قيمة الوفر
        savings = old_price - new_price
        if savings >= 1000:
            result['reason'] += f" - وفر {savings:,.0f} جنيه!"
        elif savings >= 100:
            result['reason'] += f" - وفر {savings:.0f} جنيه"
        
        self.stats['total_deals'] += 1
        
        return result

# إنشاء محلل العروض الصادق
honest_analyzer = HonestDealAnalyzer()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام صادق بدون مقارنات وهمية"""
    
    def honest_analyze_and_send():
        """تحليل صادق وإرسال"""
        
        if honest_mode_enabled[0]:
            # تحليل صادق للعرض
            analysis = honest_analyzer.analyze_deal_honestly(item, old_price, new_price, discount_percent)
            
            if not analysis['is_worth_sending']:
                print(f"🚫 رفض صادق: {item.get('name', '')[:35]}... - {analysis['reason']}")
                return
            
            # إضافة معلومات التحليل الصادق
            item['honest_analysis'] = analysis
            item['honest_confidence'] = analysis['confidence']
            item['honest_reason'] = analysis['reason']
            item['deal_category'] = analysis['category']
            
            honest_analyzer.stats['sent_alerts'] += 1
            
            print(f"✅ قبول صادق: {item.get('name', '')[:35]}... - {analysis['reason']}")
        
        # إرسال الرسالة مع الصورة
        send_honest_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=honest_analyze_and_send, daemon=True).start()

def send_honest_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه صادق مع الصورة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات التحليل الصادق
        honest_reason = item.get('honest_reason', '')
        honest_confidence = item.get('honest_confidence', 0)
        deal_category = item.get('deal_category', '')

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان صادق بناءً على نسبة الخصم الحقيقية
        if discount_percent >= 50:
            headline = "🔥 <b>HUGE DISCOUNT!</b> 🔥"
        elif discount_percent >= 35:
            headline = "✅ <b>BIG DISCOUNT!</b>"
        elif discount_percent >= 25:
            headline = "⚡ <b>GOOD DISCOUNT!</b>"
        elif discount_percent >= 15:
            headline = "💸 <b>Medium Discount</b>"
        else:
            headline = "🛍️ <b>Small Discount</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # حساب المبلغ الموفر
        savings = old_price - new_price if old_price else 0
        savings_info = f"\n💵 <b>You Save:</b> {savings:,.0f} EGP" if savings > 0 else ""
        
        # معلومات التحليل الصادق
        honest_info = ""
        if honest_reason:
            honest_info = f"\n🎯 <b>Honest Analysis:</b> {honest_reason}"
        
        if deal_category:
            honest_info += f"\n📊 <b>Category:</b> {deal_category}"
        
        confidence_row = f"\n📈 <b>Deal Score:</b> {honest_confidence}/100" if honest_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{savings_info}{confidence_row}{honest_info}

✅ <b>Honest Deal Analysis - No Fake Comparisons</b>
"""

        # أزرار بسيطة وصادقة
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🌙 Check Noon", "url": f"https://www.noon.com/egypt-en/search/?q={product_name.replace(' ', '+')}"},
                    {"text": "🛒 Check Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"}
                ]
            ]
        }
        reply_markup_json = json.dumps(reply_markup)

        sent_count = 0
        for user_id in users:
            try:
                # إرسال مع الصورة (الميزة المطلوبة)
                if img_url:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={
                            "chat_id": user_id,
                            "photo": img_url,
                            "caption": msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, timeout=25
                    )
                else:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={
                            "chat_id": user_id,
                            "text": msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, timeout=20
                    )
                
                if response.status_code == 200:
                    sent_count += 1

            except Exception as e:
                print(f"❌ خطأ إرسال للمستخدم {user_id}: {e}")
        
        if sent_count > 0:
            print(f"✅ تم إرسال تنبيه صادق لـ {sent_count} مستخدم - {deal_category}")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية
def load_db():
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
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"💾 تم حفظ {len(db):,} منتج")
    except Exception as e:
        print(f"❌ خطأ في الحفظ: {e}")

def log(msg, emoji=""):
    msg_no_links = re.sub(r'https?://\S+|www\.\S+', '', msg).strip()
    if not msg_no_links:
        return
    log_textbox.configure(state="normal")
    log_textbox.insert("end", f"{emoji} {msg_no_links}\n")
    log_textbox.see("end")
    log_textbox.configure(state="disabled")

def update_progress(val):
    progress_bar.set(val)

def add_alert_data(item, old_price, new_price, discount_percent, drop_detected=False):
    """إضافة بيانات التنبيه مع التحليل الصادق"""
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
    
    # إرسال مع التحليل الصادق
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة الأصلية (بدون تعقيدات)
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة - الطريقة الأصلية البسيطة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-images'])
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL أصلي
        url = section_url.format(page_num)
        
        if log_fn:
            honest_mode = "[HONEST]" if honest_mode_enabled[0] else ""
            log_fn(f"🟢 {honest_mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:16]:  # 16 منتج كما في الأصل
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

                # فلترة المنتجات الجديدة (إذا كان مفعل)
                if auto_new_products_mode[0] and asin in existing_asins:
                    continue

                # استخراج البيانات الأساسية
                title_el = await item.query_selector('h2 span')
                name = await title_el.inner_text() if title_el else "?"

                img_el = await item.query_selector('img.s-image')
                img = await img_el.get_attribute("src") if img_el else ""

                anchors = await item.query_selector_all('a.a-link-normal')
                long_url = ""
                for a in anchors:
                    href = await a.get_attribute("href")
                    if href and '/dp/' in href:
                        long_url = "https://www.amazon.eg" + href
                        break

                # استخراج السعر
                price_el = await item.query_selector('.a-price .a-offscreen')
                if not price_el:
                    continue
                    
                price_txt = await price_el.inner_text()
                price = parse_egp_price(price_txt)
                if not price or price < 25:
                    continue

                # السعر المشطوب
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)

                # حساب نسبة الخصم
                if strike_price and price and strike_price > price:
                    discount_percent = ((strike_price - price) / strike_price) * 100
                    
                    if discount_percent >= discount_threshold and discount_percent <= 80 and price >= 30:
                        if discount_alert_cb:
                            discount_alert_cb(
                                {
                                    "asin": asin,
                                    "name": name,
                                    "url": long_url,
                                    "img": img,
                                    "section": section,
                                    "price": price,
                                    "strike_price": strike_price,
                                    "discount_percent": discount_percent,
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

            except Exception:
                continue

        await browser.close()
        
        if log_fn:
            log_fn(f"[Page {page_num}] ✅ {new_count} NEW products")
        
        return new_count

# دوال الواجهة الأصلية
def start_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
        
    section = section_combo.get()
    pages = int(pages_entry.get())
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    honest_mode = "HONEST ON" if honest_mode_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🟢 Starting - New Products: {auto_mode}, Honest Mode: {honest_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Scraping {sec_name}...", "🟢")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🟢"),
                                discount_alert_cb=add_alert_data,
                                discount_threshold=ALERT_DISCOUNT
                            )
                            update_progress(page_num / pages)
                else:
                    sec_url = CATEGORIES[section]
                    for page_num in range(1, pages + 1):
                        if stop_flag.get("stop"):
                            break
                        await scrape_single_page(
                            section, sec_url, page_num, db,
                            log_fn=lambda m: log(m, "🟢"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات صادقة
    if honest_mode_enabled[0]:
        stats = honest_analyzer.stats
        log(f"✅ Honest Stats:")
        log(f"   📊 Total Deals Analyzed: {stats['total_deals']}")
        log(f"   🔥 High Discount (35%+): {stats['high_discount_deals']}")
        log(f"   ⚡ Medium Discount (15-34%): {stats['medium_discount_deals']}")
        log(f"   💸 Low Discount (10-14%): {stats['low_discount_deals']}")
        log(f"   📱 Alerts Sent: {stats['sent_alerts']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        
        if stats['total_deals'] > 0:
            acceptance_rate = (stats['sent_alerts'] / stats['total_deals']) * 100
            log(f"   📈 Acceptance Rate: {acceptance_rate:.1f}%")

def toggle_honest_mode():
    honest_mode_enabled[0] = not honest_mode_enabled[0]
    status = "HONEST ON" if honest_mode_enabled[0] else "OFF"
    log(f"✅ Honest Mode: {status}")

def toggle_auto_new_mode():
    auto_new_products_mode[0] = not auto_new_products_mode[0]
    status = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🆕 Auto New Products: {status}")

def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]
    status = "ON" if telegram_alerts_enabled[0] else "OFF"
    log(f"📱 Telegram: {status}")

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

def export_csv():
    with open("products_export.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price", "Discount %", "Deal Category"])
        for asin, item in db.items():
            discount_pct = item.get('discount_percent', 0)
            deal_cat = item.get('deal_category', 'Unknown')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"], discount_pct, deal_cat])
    log("Exported to CSV with honest analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== الواجهة الأصلية ====
root = ctk.CTk()
root.title("LAQTA - Honest System")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

# العنوان الأصلي
title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Honest Analysis Only", 
                             font=("Arial", 18), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

# التحكمات الأصلية
controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "5")
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# الخيارات الأصلية
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 Auto New", font=("Arial", 13), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

honest_mode_chk = ctk.CTkCheckBox(controls_frame, text="✅ Honest Mode", font=("Arial", 13), 
                                 text_color="#4CAF50", command=toggle_honest_mode)
honest_mode_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
honest_mode_chk.select()  # مفعل افتراضياً

telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="📱 Telegram", font=("Arial", 13), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=5, padx=5, pady=8, sticky="ew")
telegram_checkbox.select()

min_discount_slider = ctk.CTkSlider(controls_frame, from_=1, to=99, number_of_steps=98, width=90,
    command=set_min_discount, progress_color="#12dafb")
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=6, padx=5, pady=8, sticky="ew")

min_discount_label = ctk.CTkLabel(controls_frame, text=f"Min: {ALERT_DISCOUNT}%", font=("Arial", 12), text_color="#59ff9d")
min_discount_label.grid(row=0, column=7, padx=5, pady=8, sticky="ew")

# شريط التقدم الأصلي
progress_bar = ctk.CTkProgressBar(root, height=25, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
progress_bar.set(0.0)

# منطقة السجل الأصلية
log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=250)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

# الأزرار الأصلية
buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 190, 45
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🚀 Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#FF9800", hover_color="#e68900", text_color="#ffffff")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#9C27B0", hover_color="#7b1fa2", text_color="#ffffff")
export_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#607D8B", hover_color="#455a64", text_color="#ffffff")
clear_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

# زر الخروج الأصلي
exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=300, height=45,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 12))

load_db()

# رسائل ترحيب صادقة
log("🚀 LAQTA Honest System started!", "🟢")
log("✅ Honest Mode: ON - no fake comparisons, real discounts only", "✨")
log("📸 Telegram: ON - with photos and honest analysis", "📱")
log("🆕 Auto New: OFF - all products", "📦")
log("🎯 Expected: HONEST deals based on real discounts!", "🏆")

root.mainloop()
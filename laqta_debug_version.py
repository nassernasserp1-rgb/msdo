#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - نسخة التشخيص والإصلاح
لمعرفة سبب عدم البحث في جوجل
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

# الفئات
CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Fashion': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018165031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Home & Kitchen': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18021933031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Automotive': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017874031%2Cp_98%3A21909049031&dc&page={}&language=en",
}

# إعداد الواجهة
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# متغيرات عامة
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
advanced_google_enabled = [True]
auto_new_products_mode = [False]  # مغلق للتشخيص

ALERT_DISCOUNT = 10  # حد أدنى منخفض للتشخيص
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام التشخيص
class DebugGoogleExtractor:
    """مستخرج تشخيصي لمعرفة سبب المشكلة"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_extractions': 0,
            'extraction_attempts': 0,
            'extraction_errors': 0
        }
        
    async def debug_google_search(self, product_name: str, amazon_price: float) -> dict:
        """بحث تشخيصي في جوجل مع تفاصيل كاملة"""
        
        print(f"🔍 تشخيص جوجل: {product_name[:50]}...")
        print(f"   💰 سعر أمازون: {amazon_price:,.0f} EGP")
        
        # تحسين مصطلح البحث
        search_term = product_name.replace(',', '').replace('&', 'and')
        words = [w for w in search_term.split() if len(w) > 3][:4]
        clean_search = ' '.join(words) + " سعر مصر"
        
        print(f"   🔎 مصطلح البحث: '{clean_search}'")
        
        result = {
            'success': False,
            'error': None,
            'data_found': False,
            'search_term': clean_search
        }
        
        try:
            async with async_playwright() as p:
                print(f"   🌐 بدء Playwright...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                
                print(f"   📱 إنشاء صفحة...")
                context = await browser.new_context()
                page = await context.new_page()
                
                # رابط جوجل
                google_url = f"https://www.google.com/search?q={clean_search.replace(' ', '+')}&hl=ar&gl=EG"
                print(f"   🔗 الرابط: {google_url}")
                
                print(f"   ⏳ الذهاب لجوجل...")
                await page.goto(google_url, timeout=15000)
                await page.wait_for_timeout(3000)
                
                print(f"   📊 استخراج البيانات...")
                
                # استخراج بسيط للتشخيص
                page_data = await page.evaluate("""
                    () => {
                        const data = {
                            title: document.title,
                            url: window.location.href,
                            text_length: document.body.innerText.length,
                            has_results: false,
                            found_prices: [],
                            found_sites: []
                        };
                        
                        const bodyText = document.body.innerText || '';
                        
                        // البحث عن أسعار
                        const priceMatches = bodyText.match(/([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنيه|EGP|ج\\.م\\.)/gi);
                        if (priceMatches) {
                            data.found_prices = priceMatches.slice(0, 5);
                        }
                        
                        // البحث عن مواقع مصرية
                        const sites = ['amazon.eg', 'noon.com', 'jumia.com', 'carrefour'];
                        for (const site of sites) {
                            if (bodyText.includes(site)) {
                                data.found_sites.push(site);
                            }
                        }
                        
                        data.has_results = data.found_prices.length > 0 || data.found_sites.length > 0;
                        
                        return data;
                    }
                """)
                
                print(f"   📄 عنوان الصفحة: {page_data.get('title', 'غير محدد')}")
                print(f"   📏 طول النص: {page_data.get('text_length', 0)} حرف")
                print(f"   💰 أسعار وجدت: {len(page_data.get('found_prices', []))}")
                print(f"   🌐 مواقع وجدت: {len(page_data.get('found_sites', []))}")
                
                if page_data.get('found_prices'):
                    print(f"      💰 الأسعار: {page_data['found_prices']}")
                
                if page_data.get('found_sites'):
                    print(f"      🌐 المواقع: {page_data['found_sites']}")
                
                await browser.close()
                
                result['success'] = True
                result['data_found'] = page_data.get('has_results', False)
                self.stats['successful_extractions'] += 1
                
                if result['data_found']:
                    print(f"   ✅ تم العثور على بيانات!")
                else:
                    print(f"   ⚪ لم يتم العثور على بيانات")
                
        except Exception as e:
            print(f"   ❌ خطأ في البحث: {e}")
            result['error'] = str(e)
            self.stats['extraction_errors'] += 1
        
        finally:
            self.stats['total_searches'] += 1
        
        return result

# إنشاء مستخرج التشخيص
debug_extractor = DebugGoogleExtractor()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع تشخيص جوجل"""
    
    print(f"📱 تنبيه تليجرام: {item.get('name', '')[:40]}...")
    print(f"   💰 السعر: {old_price:,.0f} → {new_price:,.0f} EGP")
    print(f"   ⚡ الخصم: {discount_percent:.1f}%")
    
    def debug_google_and_send():
        """تشخيص جوجل وإرسال"""
        
        if advanced_google_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                print(f"   🔍 بدء البحث في جوجل...")
                debug_result = loop.run_until_complete(
                    debug_extractor.debug_google_search(item.get('name', ''), new_price)
                )
                
                if debug_result['success'] and debug_result['data_found']:
                    print(f"   ✅ جوجل: تم العثور على بيانات مقارنة")
                    item['google_debug'] = debug_result
                    item['google_confidence'] = 75  # ثقة افتراضية للتشخيص
                    item['google_recommendation'] = "تم العثور على بيانات مقارنة"
                elif debug_result['success']:
                    print(f"   ⚪ جوجل: لم يتم العثور على بيانات مقارنة")
                    item['google_confidence'] = 50
                    item['google_recommendation'] = "لم يتم العثور على بيانات مقارنة"
                else:
                    print(f"   ❌ جوجل: خطأ في البحث - {debug_result.get('error', 'غير محدد')}")
                    item['google_confidence'] = 30
                    item['google_recommendation'] = f"خطأ في البحث: {debug_result.get('error', 'غير محدد')}"
                
            except Exception as e:
                print(f"   ⚠️ خطأ في تشخيص جوجل: {e}")
                item['google_confidence'] = 40
                item['google_recommendation'] = f"خطأ في التشخيص: {e}"
            finally:
                loop.close()
        
        # إرسال الرسالة (للتشخيص)
        send_debug_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=debug_google_and_send, daemon=True).start()

def send_debug_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تشخيصي"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        google_confidence = item.get('google_confidence', 0)
        google_recommendation = item.get('google_recommendation', '')

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        headline = "🔍 <b>DEBUG TEST ALERT!</b> 🔍"
        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        confidence_row = f"\n📈 <b>Debug Confidence:</b> {google_confidence}%" if google_confidence > 0 else ""
        recommendation_row = f"\n🎯 <b>Debug Result:</b> {google_recommendation}" if google_recommendation else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{recommendation_row}

🔍 <b>DEBUG: Google Search Test</b>
"""

        sent_count = 0
        for user_id in users:
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={
                        "chat_id": user_id,
                        "text": msg,
                        "parse_mode": "HTML"
                    }, timeout=15
                )
                
                if response.status_code == 200:
                    sent_count += 1

            except Exception as e:
                print(f"❌ خطأ إرسال للمستخدم {user_id}: {e}")
        
        if sent_count > 0:
            print(f"✅ تم إرسال تنبيه تشخيصي لـ {sent_count} مستخدم")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال
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
    """إضافة بيانات التنبيه مع تشخيص مفصل"""
    asin = item.get("asin")
    
    print(f"🚨 عرض وجد: {item.get('name', '')[:40]}...")
    print(f"   🆔 ASIN: {asin}")
    print(f"   💰 السعر: {old_price:,.0f} → {new_price:,.0f} EGP")
    print(f"   ⚡ الخصم: {discount_percent:.1f}%")
    print(f"   📦 القسم: {item.get('section', 'Unknown')}")
    
    key = f"{asin}-{int(new_price)}"
    if key in notified_asins:
        print(f"   ⚠️ تم إرسال هذا العرض من قبل")
        return
    notified_asins.add(key)
    
    alerts_data.append({
        "item": item,
        "old_price": old_price,
        "new_price": new_price,
        "discount_percent": discount_percent,
        "drop_detected": drop_detected
    })
    
    print(f"   📱 سيتم إرسال تنبيه...")
    
    # إرسال مع التشخيص
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    else:
        print(f"   ⚠️ التليجرام معطل")

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة مع تشخيص مفصل
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=10):
    """سكرابة صفحة واحدة مع تشخيص مفصل"""
    
    print(f"\n🔍 تشخيص الصفحة: {section}, صفحة {page_num}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-images'])
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL
        if auto_new_products_mode[0]:
            base_url = section_url.split('&page=')[0]
            url = f"{base_url}&s=date-desc-rank&page={page_num}"
        else:
            url = section_url.format(page_num)
        
        print(f"   🔗 رابط الصفحة: {url}")
        
        if log_fn:
            mode = "[ALL]" if not auto_new_products_mode[0] else "[NEW]"
            google_mode = "[DEBUG GOOGLE]" if advanced_google_enabled[0] else ""
            log_fn(f"🔍 {mode}{google_mode} Debug: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(1500)
            print(f"   ✅ تم تحميل الصفحة")
        except Exception as e:
            print(f"   ❌ خطأ في تحميل الصفحة: {e}")
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        print(f"   📦 وجدت {len(items)} منتج في الصفحة")
        
        new_count = 0
        discount_count = 0
        processed_count = 0

        for item_idx, item in enumerate(items[:12]):  # 12 منتج للتشخيص
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

                processed_count += 1

                # فلترة المنتجات الجديدة
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
                if not price or price < 20:
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
                    discount_count += 1
                    
                    print(f"   💸 منتج {item_idx+1}: {name[:30]}...")
                    print(f"      💰 السعر: {strike_price:,.0f} → {price:,.0f} EGP")
                    print(f"      ⚡ الخصم: {discount_percent:.1f}%")
                    print(f"      ✅ يستوفي الحد الأدنى: {discount_percent >= discount_threshold}")
                    
                    if discount_percent >= discount_threshold and discount_percent <= 80 and price >= 25:
                        print(f"      📱 سيتم إرسال تنبيه...")
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
                    else:
                        print(f"      ❌ لا يستوفي الشروط")

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

            except Exception as e:
                print(f"   ⚠️ خطأ في معالجة المنتج {item_idx+1}: {e}")
                continue

        await browser.close()
        
        print(f"   📊 ملخص الصفحة:")
        print(f"      📦 منتجات معالجة: {processed_count}")
        print(f"      💸 منتجات عليها خصم: {discount_count}")
        print(f"      🆕 منتجات جديدة: {new_count}")
        
        if log_fn:
            log_fn(f"[Page {page_num}] 🔍 {new_count} NEW, {discount_count} DISCOUNTS")
        
        return new_count

# دوال الواجهة
def start_scraping():
    if running[0]:
        log("Already running.", "⚠️")
        return
        
    section = section_combo.get()
    pages = int(pages_entry.get())
    progress_bar.set(0.0)
    stop_flag["stop"] = False
    running[0] = True
    
    google_mode = "DEBUG ON" if advanced_google_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🔍 Debug Start - New Products: {auto_mode}, Debug Google: {google_mode}")
    log(f"⚡ Min Discount: {ALERT_DISCOUNT}% (حد أدنى منخفض للتشخيص)")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Debug scraping {sec_name}...", "🔍")
                        for page_num in range(1, min(pages + 1, 3)):  # أقصى 2 صفحات للتشخيص
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🔍"),
                                discount_alert_cb=add_alert_data,
                                discount_threshold=ALERT_DISCOUNT
                            )
                            update_progress(page_num / pages)
                else:
                    sec_url = CATEGORIES[section]
                    for page_num in range(1, min(pages + 1, 3)):  # أقصى 2 صفحات للتشخيص
                        if stop_flag.get("stop"):
                            break
                        await scrape_single_page(
                            section, sec_url, page_num, db,
                            log_fn=lambda m: log(m, "🔍"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Debug Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Debug Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات التشخيص
    if advanced_google_enabled[0]:
        stats = debug_extractor.stats
        log(f"🔍 Debug Google Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Extractions: {stats['successful_extractions']}")
        log(f"   ❌ Extraction Errors: {stats['extraction_errors']}")
        
        if stats['total_searches'] > 0:
            success_rate = (stats['successful_extractions'] / stats['total_searches']) * 100
            log(f"   📈 Success Rate: {success_rate:.1f}%")

def toggle_advanced_google():
    advanced_google_enabled[0] = advanced_google_chk.get()
    status = "DEBUG ON" if advanced_google_enabled[0] else "OFF"
    log(f"🔍 Debug Google: {status}")

def toggle_auto_new_mode():
    auto_new_products_mode[0] = auto_new_chk.get()
    status = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🆕 Auto New Products: {status}")

def toggle_telegram_alert():
    telegram_alerts_enabled[0] = not telegram_alerts_enabled[0]

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

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== MAIN ROOT ====
root = ctk.CTk()
root.title("LAQTA - Debug Version")
root.geometry("1600x1000")
root.minsize(1400, 800)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - DEBUG MODE", font=("SST Arabic Medium", 55), text_color="#ff6666")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🔍 نسخة التشخيص - لمعرفة سبب عدم البحث في جوجل", 
                             font=("Arial", 18, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["Electronics", "Beauty"],  # مبسط للتشخيص
    width=170, font=("Arial", 15), button_color="#ff6666")
section_combo.set("Beauty")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "1")  # صفحة واحدة فقط للتشخيص
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 13, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")
# معطل للتشخيص

# التشخيص المتقدم
advanced_google_chk = ctk.CTkCheckBox(controls_frame, text="🔍 Debug Google", font=("Arial", 13, "bold"), 
                                     text_color="#ff6666", command=toggle_advanced_google)
advanced_google_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
advanced_google_chk.select()

telegram_checkbox = ctk.CTkCheckBox(controls_frame, text="📱 Telegram", font=("Arial", 13), text_color="#13e6a7",
    command=toggle_telegram_alert)
telegram_checkbox.grid(row=0, column=5, padx=5, pady=8, sticky="ew")
telegram_checkbox.select()

min_discount_slider = ctk.CTkSlider(controls_frame, from_=1, to=99, number_of_steps=98, width=90,
    command=set_min_discount, progress_color="#ff6666")
min_discount_slider.set(ALERT_DISCOUNT)
min_discount_slider.grid(row=0, column=6, padx=5, pady=8, sticky="ew")

min_discount_label = ctk.CTkLabel(controls_frame, text=f"Min: {ALERT_DISCOUNT}%", font=("Arial", 12), text_color="#ff6666")
min_discount_label.grid(row=0, column=7, padx=5, pady=8, sticky="ew")

progress_bar = ctk.CTkProgressBar(root, height=25, progress_color="#ff6666", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#ff9999", border_width=0, height=280)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

btn_w, btn_h = 200, 50
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🔍 Debug Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ff6666", hover_color="#ff4444", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ea4335", hover_color="#d93025", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#34a853", hover_color="#137333", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Debug Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#fbbc04", hover_color="#f9ab00", text_color="#000000")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=350, height=50,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#ff6666")
exit_btn.grid(row=6, column=0, pady=(8, 15))

load_db()

# رسائل ترحيب تشخيصية
log("🔍 LAQTA Debug Mode started!", "🚀")
log("🎯 Debug Purpose: معرفة سبب عدم البحث في جوجل", "⚠️")
log("📊 Debug Settings: حد أدنى 10%، صفحة واحدة، تفاصيل كاملة", "🔧")
log("🆕 New Products: OFF - جميع المنتجات", "📦")
log("📱 Expected: تشخيص مفصل لكل خطوة!", "🔍")

root.mainloop()
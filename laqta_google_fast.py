#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - مقارنة جوجل السريعة والفعالة
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
google_comparison_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام مقارنة جوجل السريع والمباشر
class FastGoogleComparator:
    """مقارن الأسعار السريع عن طريق جوجل - نسخة مبسطة وفعالة"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_finds': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'cache_hits': 0
        }
        self.cache = {}
        self.timeout_seconds = 8  # مهلة قصيرة للسرعة
    
    def extract_key_words(self, product_name: str) -> str:
        """استخراج الكلمات المفتاحية الهامة فقط"""
        
        # العلامات التجارية المهمة
        key_brands = [
            'samsung', 'apple', 'iphone', 'xiaomi', 'huawei', 'sony', 'lg', 
            'canon', 'hp', 'dell', 'anker', 'baseus', 'joyroom', 'redmi'
        ]
        
        # تنظيف النص
        clean_text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', product_name.lower())
        words = clean_text.split()
        
        # العثور على العلامة التجارية
        brand_found = ""
        for brand in key_brands:
            if brand in clean_text:
                brand_found = brand
                break
        
        # أخذ أهم 2-3 كلمات
        important_words = []
        if brand_found:
            important_words.append(brand_found)
        
        # إضافة كلمات أخرى مهمة
        for word in words:
            if (len(word) > 3 and 
                word not in important_words and 
                word not in ['amazon', 'choice', 'brand', 'original']):
                important_words.append(word)
                if len(important_words) >= 3:
                    break
        
        search_term = ' '.join(important_words) + " price egypt"
        return search_term
    
    async def quick_google_search(self, product_name: str, amazon_price: float) -> dict:
        """بحث سريع في جوجل مع التركيز على السرعة"""
        
        search_key = f"fast_{product_name[:25]}_{amazon_price}"
        
        # فحص الكاش أولاً
        if search_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[search_key]
        
        search_term = self.extract_key_words(product_name)
        print(f"🔍 بحث سريع: {search_term}")
        
        result = {
            'competitors': [],
            'amazon_price': amazon_price,
            'is_good_deal': False,
            'confidence': 30,
            'reason': 'لا توجد مقارنة',
            'rank': 0,
            'total_stores': 0
        }
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-images',
                        '--disable-javascript',
                        '--disable-css',
                        '--disable-plugins',
                        '--window-size=1024,768'
                    ]
                )
                
                page = await browser.new_page()
                
                # رابط جوجل شوبينج مباشر
                google_url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}&tbm=shop&hl=ar&gl=EG"
                
                await page.goto(google_url, timeout=self.timeout_seconds * 1000)
                await page.wait_for_timeout(2000)  # انتظار قصير
                
                # استخراج سريع للأسعار
                prices_found = await page.evaluate("""
                    () => {
                        const prices = [];
                        const egyptianSites = ['jumia', 'noon', 'souq', 'btech', 'amazon.eg', 'carrefour'];
                        
                        // البحث في جميع النصوص للأسعار
                        const allText = document.body.textContent || '';
                        
                        // البحث عن الأسعار بالجنيه المصري
                        const priceMatches = allText.matchAll(/([0-9,]+(?:\.[0-9]+)?)\s*(?:جنيه|EGP|ج\.م)/gi);
                        
                        for (const match of priceMatches) {
                            const price = parseFloat(match[1].replace(/,/g, ''));
                            if (price > 30 && price < 200000) {
                                prices.push(price);
                            }
                        }
                        
                        // إزالة التكرار وترتيب
                        const uniquePrices = [...new Set(prices)].sort((a, b) => a - b);
                        
                        return uniquePrices.slice(0, 8); // أول 8 أسعار
                    }
                """)
                
                await browser.close()
                
                if prices_found && len(prices_found) >= 2:
                    # تحليل سريع
                    market_prices = [p for p in prices_found if p != amazon_price]
                    
                    if market_prices:
                        avg_price = sum(market_prices) / len(market_prices)
                        min_price = min(market_prices)
                        
                        # حساب ترتيب أمازون
                        cheaper_count = sum(1 for p in market_prices if p > amazon_price)
                        total_competitors = len(market_prices)
                        amazon_rank = total_competitors - cheaper_count + 1
                        
                        result['competitors'] = market_prices
                        result['total_stores'] = total_competitors
                        result['rank'] = amazon_rank
                        
                        # تحديد جودة العرض بسرعة
                        if amazon_rank == 1:
                            result['is_good_deal'] = True
                            result['confidence'] = 90
                            result['reason'] = f"🔥 الأرخص من {total_competitors} متاجر"
                        elif amazon_rank <= 2:
                            result['is_good_deal'] = True
                            result['confidence'] = 80
                            result['reason'] = f"✅ ثاني أرخص من {total_competitors} متاجر"
                        elif amazon_price < avg_price:
                            result['is_good_deal'] = True
                            result['confidence'] = 70
                            result['reason'] = f"⚡ أرخص من المتوسط ({avg_price:,.0f})"
                        elif amazon_rank <= total_competitors * 0.6:
                            result['is_good_deal'] = True
                            result['confidence'] = 60
                            result['reason'] = f"⚠️ ترتيب {amazon_rank} من {total_competitors}"
                        else:
                            result['is_good_deal'] = False
                            result['confidence'] = 40
                            result['reason'] = f"❌ ترتيب {amazon_rank} من {total_competitors}"
                        
                        print(f"   📊 {total_competitors} منافس، ترتيب {amazon_rank}")
                        print(f"   🎯 {result['reason']}")
                        
                        self.stats['successful_finds'] += 1
                
        except Exception as e:
            print(f"   ⚠️ خطأ سريع: {e}")
        
        self.stats['total_searches'] += 1
        
        # حفظ في الكاش
        self.cache[search_key] = result
        
        return result

# إنشاء مقارن جوجل السريع
fast_google_comparator = FastGoogleComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع مقارنة جوجل السريعة"""
    
    def fast_google_compare_and_send():
        """مقارنة سريعة عن طريق جوجل وإرسال"""
        
        if google_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    fast_google_comparator.quick_google_search(item.get('name', ''), new_price)
                )
                
                # فلترة أكثر تساهلاً للسرعة
                if not comparison_result['is_good_deal'] and comparison_result['confidence'] < 50:
                    print(f"🚫 رفض سريع: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    fast_google_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات جوجل السريعة
                item['google_analysis'] = comparison_result
                item['google_confidence'] = comparison_result['confidence']
                item['google_reason'] = comparison_result['reason']
                item['google_rank'] = comparison_result['rank']
                item['google_competitors'] = comparison_result['total_stores']
                
                fast_google_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة السريعة: {e}")
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=fast_google_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع معلومات جوجل السريعة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات جوجل السريعة
        google_reason = item.get('google_reason', '')
        google_confidence = item.get('google_confidence', 0)
        google_rank = item.get('google_rank', 0)
        google_competitors = item.get('google_competitors', 0)

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على الترتيب
        if google_rank == 1:
            headline = "🔥 <b>CHEAPEST PRICE!</b> 🔥"
        elif google_rank <= 2:
            headline = "✅ <b>TOP DEAL!</b>"
        elif google_confidence >= 70:
            headline = "⚡ <b>GOOD DEAL!</b>"
        else:
            headline = "💸 <b>Deal Alert!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات مقارنة سريعة
        google_info = ""
        if google_reason:
            google_info = f"\n🎯 <b>Quick Check:</b> {google_reason}"
        
        if google_competitors > 0:
            google_info += f"\n🏪 <b>vs {google_competitors} competitors</b>"
        
        confidence_row = f"\n📊 <b>Score:</b> {google_confidence}/100" if google_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{google_info}

⚡ <b>Fast Google Comparison</b>
"""

        # أزرار سريعة
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Amazon", "url": url}],
                [{"text": "🔍 Google", "url": f"https://www.google.com/search?q={product_name.replace(' ', '+')}&tbm=shop"}],
                [{"text": "🏪 Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"}]
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
                        }, timeout=10
                    )
                
                if response.status_code == 200:
                    sent_count += 1

            except Exception as e:
                print(f"❌ خطأ إرسال للمستخدم {user_id}: {e}")
        
        if sent_count > 0:
            rank_text = f"ترتيب {google_rank}" if google_rank > 0 else "مقارنة سريعة"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - {rank_text}")

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
    """إضافة بيانات التنبيه مع مقارنة جوجل السريعة"""
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
    
    # إرسال مع مقارنة جوجل السريعة
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة السريعة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة مع التركيز على السرعة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript', '--disable-css']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL محسن
        if auto_new_products_mode[0]:
            base_url = section_url.split('&page=')[0]
            url = f"{base_url}&s=date-desc-rank&page={page_num}"
        else:
            url = section_url.format(page_num)
        
        if log_fn:
            mode = "[NEW]" if auto_new_products_mode[0] else ""
            google_mode = "[FAST GOOGLE]" if google_comparison_enabled[0] else ""
            log_fn(f"⚡ {mode}{google_mode} Fast Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)  # انتظار أقل للسرعة
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:8]:  # أول 8 منتجات للسرعة
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

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
                    
                    if discount_percent >= discount_threshold and discount_percent <= 70 and price >= 30:
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
            log_fn(f"[Page {page_num}] ⚡ {new_count} NEW products")
        
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
    
    google_mode = "FAST ON" if google_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"⚡ Fast Start - New Products: {auto_mode}, Fast Google: {google_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Fast Scraping {sec_name}...", "⚡")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "⚡"),
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
                            log_fn=lambda m: log(m, "⚡"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Fast Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Fast Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات جوجل السريعة
    if google_comparison_enabled[0]:
        stats = fast_google_comparator.stats
        log(f"⚡ Fast Google Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Finds: {stats['successful_finds']}")
        log(f"   📱 Validated: {stats['validated_deals']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        
        if stats['total_searches'] > 0:
            success_rate = (stats['validated_deals'] / stats['total_searches']) * 100
            log(f"   📈 Success Rate: {success_rate:.1f}%")

def toggle_google_comparison():
    google_comparison_enabled[0] = google_comparison_chk.get()
    status = "FAST ON" if google_comparison_enabled[0] else "OFF"
    log(f"⚡ Fast Google Comparison: {status}")

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

def export_csv():
    with open("products_export.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price"])
        for asin, item in db.items():
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"]])
    log("Exported to CSV.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== MAIN ROOT ====
root = ctk.CTk()
root.title("LAQTA - Fast Google Checker")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - FAST GOOGLE", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="⚡ النسخة السريعة: مقارنة سريعة مع جوجل + فلترة ذكية", 
                             font=("Arial", 18, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "4")  # عدد أقل للسرعة العالية
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 13, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")
auto_new_chk.select()

# مقارنة جوجل السريعة
google_comparison_chk = ctk.CTkCheckBox(controls_frame, text="⚡ Fast Google", font=("Arial", 13, "bold"), 
                                       text_color="#4285f4", command=toggle_google_comparison)
google_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
google_comparison_chk.select()

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

progress_bar = ctk.CTkProgressBar(root, height=25, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=250)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

btn_w, btn_h = 190, 45
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="⚡ Fast Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4285f4", hover_color="#1a73e8", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ea4335", hover_color="#d93025", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#34a853", hover_color="#137333", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Fast Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#fbbc04", hover_color="#f9ab00", text_color="#000000")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#12dafb", hover_color="#59ff9d", text_color="#111927")
export_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#54fac8", hover_color="#12dafb", text_color="#111927")
clear_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=300, height=45,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 12))

load_db()

# رسائل ترحيب سريعة
log("⚡ LAQTA Fast Google started!", "🚀")
log("🔍 Fast Google: ON - مقارنة سريعة في 8 ثواني", "✨")
log("🆕 New Products: ON - منتجات جديدة فقط", "💡")
log("⚡ Speed Mode: ON - أولوية للسرعة والكفاءة", "🏃")
log("📱 Expected: FAST high-quality deals!", "🏆")

root.mainloop()
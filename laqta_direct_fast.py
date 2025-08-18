#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - البحث المباشر السريع في المواقع المصرية
بدون جوجل - سرعة قصوى - نتائج مضمونة
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
direct_comparison_enabled = [True]
auto_new_products_mode = [True]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام البحث المباشر السريع
class FastDirectComparator:
    """مقارن الأسعار المباشر السريع - بحث مباشر في المواقع المصرية"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_finds': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'cache_hits': 0,
            'site_errors': 0,
            'fast_finds': 0
        }
        self.cache = {}
        self.last_search_time = 0
        self.search_delay = 1  # ثانية واحدة فقط بين البحثات للسرعة
        
        # المواقع المصرية للبحث المباشر (سريعة)
        self.egyptian_sites = {
            'noon': {
                'url': 'https://www.noon.com/egypt-en/search/?q={}',
                'price_selectors': ['.priceNow', '.price-now', '.final-price'],
                'timeout': 5000
            },
            'jumia': {
                'url': 'https://www.jumia.com.eg/catalog/?q={}',
                'price_selectors': ['.prc', '.price', '.current-price'],
                'timeout': 5000
            }
        }
    
    def extract_simple_keywords(self, product_name: str) -> str:
        """استخراج بسيط وسريع للكلمات المفتاحية"""
        
        # علامات تجارية مهمة فقط
        important_brands = {
            'samsung': 'samsung',
            'apple': 'apple',
            'iphone': 'iphone',
            'xiaomi': 'xiaomi',
            'redmi': 'redmi',
            'sony': 'sony',
            'anker': 'anker',
            'joyroom': 'joyroom',
            'canon': 'canon',
            'hp': 'hp'
        }
        
        name_lower = product_name.lower()
        
        # البحث عن العلامة التجارية
        brand_found = ""
        for brand, clean_name in important_brands.items():
            if brand in name_lower:
                brand_found = clean_name
                break
        
        # استخراج أرقام مهمة (موديل)
        numbers = re.findall(r'\b(\d+(?:gb|w|mah|ml)?)\b', name_lower)
        important_number = numbers[0] if numbers else ""
        
        # إنشاء مصطلح بحث بسيط
        if brand_found and important_number:
            search_term = f"{brand_found} {important_number}"
        elif brand_found:
            search_term = brand_found
        else:
            # أخذ أول كلمتين فقط
            words = [w for w in product_name.split()[:2] if len(w) > 3]
            search_term = ' '.join(words)
        
        return search_term.strip()
    
    async def fast_site_search(self, site_name: str, site_config: dict, search_term: str) -> list:
        """بحث سريع في موقع واحد"""
        
        prices = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript', '--disable-css']
                )
                
                page = await browser.new_page()
                
                # البحث في الموقع
                search_url = site_config['url'].format(search_term.replace(' ', '+'))
                
                await page.goto(search_url, timeout=site_config['timeout'])
                await page.wait_for_timeout(2000)  # انتظار قصير جداً
                
                # استخراج الأسعار بسرعة
                for selector in site_config['price_selectors']:
                    try:
                        price_elements = await page.query_selector_all(selector)
                        for element in price_elements[:5]:  # أول 5 عناصر فقط
                            price_text = await element.inner_text()
                            
                            # استخراج سريع للأسعار
                            price_match = re.search(r'([0-9,]+(?:\.[0-9]+)?)', price_text.replace(',', ''))
                            if price_match:
                                price = float(price_match.group(1))
                                if 20 <= price <= 50000:  # أسعار منطقية
                                    prices.append(price)
                        
                        if prices:  # إذا وجدنا أسعار، نتوقف
                            break
                            
                    except Exception:
                        continue
                
                await browser.close()
                
        except Exception as e:
            self.stats['site_errors'] += 1
        
        return prices
    
    async def lightning_fast_comparison(self, product_name: str, amazon_price: float) -> dict:
        """مقارنة سريعة جداً مع المواقع المصرية"""
        
        # تحكم في السرعة
        current_time = time.time()
        if current_time - self.last_search_time < self.search_delay:
            await asyncio.sleep(self.search_delay - (current_time - self.last_search_time))
        self.last_search_time = time.time()
        
        search_term = self.extract_simple_keywords(product_name)
        cache_key = f"fast_{search_term}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"⚡ بحث سريع: {search_term}")
        
        result = {
            'found_prices': [],
            'sites_checked': [],
            'amazon_price': amazon_price,
            'is_good_deal': False,
            'confidence': 40,
            'reason': 'لم يتم العثور على أسعار',
            'search_time': 0
        }
        
        start_time = time.time()
        
        # بحث متوازي سريع في المواقع
        tasks = []
        for site_name, site_config in self.egyptian_sites.items():
            task = self.fast_site_search(site_name, site_config, search_term)
            tasks.append((site_name, task))
        
        # تشغيل جميع البحثات بالتوازي
        all_prices = []
        sites_found = []
        
        for site_name, task in tasks:
            try:
                prices = await asyncio.wait_for(task, timeout=6)  # مهلة قصيرة جداً
                if prices:
                    all_prices.extend(prices)
                    sites_found.append(site_name)
                    print(f"   ✅ {site_name}: {len(prices)} أسعار")
                else:
                    print(f"   ⚪ {site_name}: لا توجد أسعار")
            except asyncio.TimeoutError:
                print(f"   ⏱️ {site_name}: انتهت المهلة")
            except Exception as e:
                print(f"   ❌ {site_name}: خطأ")
        
        # معالجة النتائج
        if all_prices:
            # إزالة التكرار وترتيب
            unique_prices = sorted(list(set(all_prices)))
            
            # فلترة سريعة للأسعار الغريبة
            if len(unique_prices) > 3:
                median_price = statistics.median(unique_prices)
                filtered_prices = [p for p in unique_prices if 0.3 * median_price <= p <= 3 * median_price]
                if len(filtered_prices) >= 2:
                    unique_prices = filtered_prices
            
            result['found_prices'] = unique_prices
            result['sites_checked'] = sites_found
            
            if len(unique_prices) >= 2:
                # تحليل سريع
                avg_price = statistics.mean(unique_prices)
                min_price = min(unique_prices)
                
                # حساب ترتيب أمازون
                cheaper_count = sum(1 for p in unique_prices if p > amazon_price)
                total_competitors = len(unique_prices)
                amazon_rank = total_competitors - cheaper_count + 1
                
                # تحديد جودة العرض بسرعة
                if amazon_rank == 1:
                    result['confidence'] = 85
                    result['reason'] = f"🔥 الأرخص من {total_competitors} أسعار!"
                    result['is_good_deal'] = True
                elif amazon_rank == 2:
                    result['confidence'] = 75
                    result['reason'] = f"✅ ثاني أرخص من {total_competitors} أسعار"
                    result['is_good_deal'] = True
                elif amazon_price < avg_price:
                    result['confidence'] = 70
                    result['reason'] = f"⚡ أرخص من المتوسط ({avg_price:,.0f})"
                    result['is_good_deal'] = True
                else:
                    result['confidence'] = 50
                    result['reason'] = f"⚠️ ترتيب {amazon_rank} من {total_competitors}"
                    result['is_good_deal'] = amazon_rank <= total_competitors * 0.7  # أكثر تساهلاً
                
                print(f"   📊 {total_competitors} أسعار | المتوسط: {avg_price:.0f} | الأقل: {min_price:.0f}")
                print(f"   🎯 أمازون: {amazon_price:.0f} (ترتيب {amazon_rank}) | {result['reason']}")
                
                self.stats['successful_finds'] += 1
                
            else:
                result['confidence'] = 60
                result['reason'] = f"⚪ سعر واحد ({unique_prices[0]:.0f}) من {sites_found[0]}"
                result['is_good_deal'] = True  # نقبل لأن وجدنا مقارنة
        
        result['search_time'] = time.time() - start_time
        self.stats['total_searches'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result

# إنشاء مقارن البحث المباشر السريع
fast_direct_comparator = FastDirectComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة المباشرة السريعة"""
    
    def fast_direct_compare_and_send():
        """مقارنة مباشرة سريعة وإرسال"""
        
        if direct_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    fast_direct_comparator.lightning_fast_comparison(item.get('name', ''), new_price)
                )
                
                # قبول العروض بثقة 50% فأكثر (تساهل للسرعة)
                if not comparison_result['is_good_deal'] and comparison_result['confidence'] < 50:
                    print(f"🚫 رفض سريع: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    fast_direct_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة السريعة
                item['direct_analysis'] = comparison_result
                item['direct_confidence'] = comparison_result['confidence']
                item['direct_reason'] = comparison_result['reason']
                item['found_prices'] = comparison_result['found_prices']
                item['sites_checked'] = comparison_result['sites_checked']
                item['search_time'] = comparison_result['search_time']
                
                fast_direct_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة السريعة: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة
                if discount_percent >= 30:
                    item['direct_confidence'] = 65
                    item['direct_reason'] = "خصم كبير - قبول مباشر"
                    fast_direct_comparator.stats['validated_deals'] += 1
                else:
                    return
            finally:
                loop.close()
        
        # إرسال الرسالة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=fast_direct_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع معلومات المقارنة السريعة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة السريعة
        direct_reason = item.get('direct_reason', '')
        direct_confidence = item.get('direct_confidence', 0)
        found_prices = item.get('found_prices', [])
        sites_checked = item.get('sites_checked', [])
        search_time = item.get('search_time', 0)

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على الثقة
        if direct_confidence >= 80:
            headline = "⚡ <b>LIGHTNING FAST DEAL!</b> ⚡"
        elif direct_confidence >= 70:
            headline = "🚀 <b>DIRECT VERIFIED DEAL!</b>"
        elif direct_confidence >= 60:
            headline = "✅ <b>FAST DEAL FOUND!</b>"
        else:
            headline = "💸 <b>Quick Deal Alert!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات السوق
        market_info = ""
        if found_prices:
            avg_market = sum(found_prices) / len(found_prices)
            min_market = min(found_prices)
            market_info = f"\n📊 <b>Market:</b> Avg {avg_market:,.0f} | Min {min_market:,.0f}"
        
        # معلومات البحث السريع
        speed_info = ""
        if sites_checked:
            speed_info = f"\n🌐 <b>Checked:</b> {', '.join(sites_checked)}"
        
        if search_time > 0:
            speed_info += f"\n⚡ <b>Search Time:</b> {search_time:.1f}s"
        
        # معلومات المقارنة
        direct_info = ""
        if direct_reason:
            direct_info = f"\n🎯 <b>Direct Analysis:</b> {direct_reason}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {direct_confidence}%" if direct_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{market_info}{speed_info}{direct_info}

⚡ <b>Lightning Fast Direct Comparison</b>
"""

        # أزرار سريعة
        reply_markup = {
            "inline_keyboard": [
                [{"text": "⚡ Buy Now", "url": url}],
                [{"text": "🏪 Noon", "url": f"https://www.noon.com/egypt-en/search/?q={product_name.replace(' ', '+')}"}],
                [{"text": "🛒 Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"}]
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
            speed_text = f"⚡{search_time:.1f}s" if search_time > 0 else "سريع"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - {speed_text}")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية (مبسطة للسرعة)
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
    """إضافة بيانات التنبيه مع المقارنة السريعة"""
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
    
    # إرسال مع المقارنة السريعة
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة السريعة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة مع التركيز على السرعة القصوى"""
    
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
            direct_mode = "[DIRECT FAST]" if direct_comparison_enabled[0] else ""
            log_fn(f"⚡ {mode}{direct_mode} Lightning: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)  # انتظار قصير جداً
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:8]:  # 8 منتجات فقط للسرعة القصوى
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
                if not price or price < 30:
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
                    
                    if discount_percent >= discount_threshold and discount_percent <= 65 and price >= 35:
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
    
    direct_mode = "LIGHTNING ON" if direct_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"⚡ Lightning Start - New Products: {auto_mode}, Direct Fast: {direct_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Lightning scraping {sec_name}...", "⚡")
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
            log("✅ Lightning Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Lightning Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات البحث المباشر السريع
    if direct_comparison_enabled[0]:
        stats = fast_direct_comparator.stats
        log(f"⚡ Lightning Direct Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Finds: {stats['successful_finds']}")
        log(f"   📱 Validated: {stats['validated_deals']}")
        log(f"   🚫 Rejected: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ❌ Site Errors: {stats['site_errors']}")
        log(f"   ⚡ Fast Finds: {stats['fast_finds']}")
        
        if stats['total_searches'] > 0:
            success_rate = (stats['successful_finds'] / stats['total_searches']) * 100
            validation_rate = (stats['validated_deals'] / stats['total_searches']) * 100
            log(f"   📈 Find Rate: {success_rate:.1f}%")
            log(f"   📈 Validation Rate: {validation_rate:.1f}%")

def toggle_direct_comparison():
    direct_comparison_enabled[0] = direct_comparison_chk.get()
    status = "LIGHTNING ON" if direct_comparison_enabled[0] else "OFF"
    log(f"⚡ Lightning Direct Comparison: {status}")

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
root.title("LAQTA - Lightning Fast Direct Checker")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA - LIGHTNING FAST", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="⚡ البحث المباشر السريع: بدون جوجل - سرعة قصوى - نتائج مضمونة", 
                             font=("Arial", 18, "bold"), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Electronics")  # نبدأ بـ Electronics
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "2")  # عدد قليل للسرعة القصوى
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# المنتجات الجديدة
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 New Only", font=("Arial", 13, "bold"), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")
auto_new_chk.select()

# المقارنة المباشرة السريعة
direct_comparison_chk = ctk.CTkCheckBox(controls_frame, text="⚡ Lightning Direct", font=("Arial", 13, "bold"), 
                                       text_color="#4285f4", command=toggle_direct_comparison)
direct_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
direct_comparison_chk.select()

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

start_btn = ctk.CTkButton(buttons_frame, text="⚡ Lightning Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4285f4", hover_color="#1a73e8", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#ea4335", hover_color="#d93025", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#34a853", hover_color="#137333", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Lightning Stats", command=show_stats, width=btn_w, height=btn_h,
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
log("⚡ LAQTA Lightning Fast started!", "🚀")
log("🚀 Direct Search: ON - بحث مباشر في المواقع المصرية", "✨")
log("⚡ Lightning Speed: ON - سرعة قصوى بدون جوجل", "💡")
log("🎯 Target Sites: Noon + Jumia (أسرع المواقع)", "🎯")
log("🆕 New Products: ON - منتجات جديدة فقط", "🎯")
log("📱 Expected: LIGHTNING FAST verified deals!", "🏆")

root.mainloop()
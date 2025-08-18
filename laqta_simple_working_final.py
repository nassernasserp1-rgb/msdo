#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النسخة البسيطة الشغالة
مقارنة بسيطة مع نون + قبول ذكي + روابط صحيحة
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
import urllib.parse

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
smart_comparison_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 15
alerts_data = []
notified_asins = set()
existing_asins = set()

class SimpleWorkingComparator:
    """مقارن بسيط وشغال - يركز على النتائج"""
    
    def __init__(self):
        self.stats = {
            'total_products': 0,
            'products_sent': 0,
            'noon_comparisons': 0,
            'smart_accepts': 0,
            'avg_market_price': 0,
            'total_market_value': 0
        }
        
        # العلامات التجارية المعروفة (للقبول المباشر)
        self.trusted_brands = {
            'samsung', 'xiaomi', 'apple', 'sony', 'lg', 'anker', 'tp-link', 
            'wd', 'sandisk', 'logitech', 'honor', 'huawei', 'sharp', 'haier'
        }
    
    def get_simple_search_term(self, product_name: str) -> str:
        """استخراج مصطلح بحث بسيط"""
        
        # أخذ أول 3 كلمات مهمة فقط
        words = []
        for word in product_name.split()[:5]:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if len(clean_word) > 2:
                words.append(clean_word)
            if len(words) >= 3:
                break
        
        return ' '.join(words)
    
    def get_brand(self, product_name: str) -> str:
        """استخراج العلامة التجارية"""
        name_lower = product_name.lower()
        
        for brand in self.trusted_brands:
            if brand in name_lower:
                return brand
        
        return 'unknown'
    
    async def simple_noon_check(self, search_term: str) -> dict:
        """فحص بسيط في نون"""
        
        result = {'found_prices': False, 'prices': [], 'average': 0}
        
        try:
            # استخدام requests بدلاً من playwright للبساطة
            import requests
            
            search_url = f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(search_term)}"
            
            response = requests.get(search_url, timeout=8, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                content = response.text
                
                # البحث البسيط عن الأسعار في HTML
                price_matches = re.findall(r'(\d{2,6})\s*(?:جنيه|EGP)', content, re.IGNORECASE)
                
                prices = []
                for match in price_matches[:15]:  # أول 15 نتيجة
                    try:
                        price = float(match.replace(',', ''))
                        if 30 <= price <= 50000:
                            prices.append(price)
                    except:
                        continue
                
                if len(prices) >= 3:
                    # إزالة التكرار والترتيب
                    unique_prices = sorted(list(set(prices)))
                    
                    # أخذ أول 8 أسعار
                    if len(unique_prices) > 8:
                        unique_prices = unique_prices[:8]
                    
                    result['found_prices'] = True
                    result['prices'] = unique_prices
                    result['average'] = statistics.mean(unique_prices)
                    
                    self.stats['noon_comparisons'] += 1
                    print(f"      🌙 نون: وجدت {len(unique_prices)} أسعار، متوسط {result['average']:,.0f}")
                    
        except Exception as e:
            print(f"      ⚠️ نون: خطأ - {e}")
        
        return result
    
    def simple_comparison(self, product_name: str, amazon_price: float, discount_percent: float) -> dict:
        """مقارنة بسيطة وشغالة"""
        
        search_term = self.get_simple_search_term(product_name)
        brand = self.get_brand(product_name)
        
        print(f"🔍 مقارنة بسيطة: {product_name[:35]}...")
        print(f"   🔎 البحث: '{search_term}' | 🏷️ العلامة: {brand}")
        
        result = {
            'amazon_price': amazon_price,
            'market_average': 0,
            'is_good_deal': True,
            'confidence': 65,
            'reason': 'منتج مقبول',
            'comparison_type': 'simple_smart',
            'brand': brand,
            'discount_percent': discount_percent
        }
        
        # محاولة بحث بسيط في نون
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            noon_result = loop.run_until_complete(
                asyncio.wait_for(self.simple_noon_check(search_term), timeout=10)
            )
            
            if noon_result['found_prices']:
                # مقارنة ناجحة
                market_average = noon_result['average']
                market_prices = noon_result['prices']
                
                result['market_average'] = market_average
                self.stats['total_market_value'] += market_average
                
                # حساب الفرق
                vs_market_percent = ((market_average - amazon_price) / market_average) * 100
                
                if vs_market_percent > 25:
                    result['confidence'] = 90
                    result['reason'] = f"🔥 أرخص بـ {vs_market_percent:.0f}% من متوسط السوق"
                elif vs_market_percent > 15:
                    result['confidence'] = 85
                    result['reason'] = f"✅ أرخص بـ {vs_market_percent:.0f}% من متوسط السوق"
                elif vs_market_percent > 5:
                    result['confidence'] = 80
                    result['reason'] = f"⚡ أرخص بـ {vs_market_percent:.0f}% من متوسط السوق"
                elif vs_market_percent > -10:
                    result['confidence'] = 75
                    result['reason'] = f"💸 قريب من متوسط السوق"
                else:
                    result['confidence'] = 70
                    result['reason'] = f"⚠️ أغلى من متوسط السوق بـ {abs(vs_market_percent):.0f}%"
                
                result['comparison_type'] = 'noon_success'
                
                print(f"   📊 مقارنة ناجحة:")
                print(f"      💰 متوسط السوق: {market_average:,.0f} EGP")
                print(f"      🎯 أمازون: {amazon_price:,.0f} EGP")
                print(f"   {result['reason']}")
                
            else:
                # لم نجد أسعار - قبول ذكي
                result = self.smart_brand_accept(brand, amazon_price, discount_percent)
                self.stats['smart_accepts'] += 1
            
            loop.close()
            
        except Exception as e:
            print(f"   ❌ خطأ في المقارنة: {e}")
            result = self.smart_brand_accept(brand, amazon_price, discount_percent)
            self.stats['smart_accepts'] += 1
        
        self.stats['total_products'] += 1
        
        return result
    
    def smart_brand_accept(self, brand: str, amazon_price: float, discount_percent: float) -> dict:
        """قبول ذكي بناءً على العلامة التجارية والخصم"""
        
        result = {
            'amazon_price': amazon_price,
            'market_average': 0,
            'is_good_deal': True,
            'confidence': 70,
            'reason': 'قبول ذكي',
            'comparison_type': 'smart_brand_accept',
            'brand': brand,
            'discount_percent': discount_percent
        }
        
        # تقييم العلامة التجارية
        if brand in self.trusted_brands:
            if brand in ['samsung', 'apple', 'sony', 'anker']:  # علامات ممتازة
                result['confidence'] = 85
                result['reason'] = f"✅ علامة ممتازة ({brand}) - قبول مباشر"
            elif brand in ['xiaomi', 'lg', 'tp-link', 'wd']:  # علامات جيدة
                result['confidence'] = 80
                result['reason'] = f"⚡ علامة جيدة ({brand}) - قبول مباشر"
            else:  # علامات معروفة
                result['confidence'] = 75
                result['reason'] = f"💸 علامة معروفة ({brand}) - قبول مباشر"
        else:
            # علامة غير معروفة - نعتمد على الخصم
            if discount_percent >= 40:
                result['confidence'] = 80
                result['reason'] = f"🔥 خصم كبير {discount_percent:.0f}% - قبول"
            elif discount_percent >= 25:
                result['confidence'] = 75
                result['reason'] = f"⚡ خصم جيد {discount_percent:.0f}% - قبول"
            elif discount_percent >= 15:
                result['confidence'] = 70
                result['reason'] = f"💸 خصم متوسط {discount_percent:.0f}% - قبول"
            else:
                result['confidence'] = 65
                result['reason'] = f"⚠️ خصم بسيط {discount_percent:.0f}% - قبول محدود"
        
        print(f"   🧠 قبول ذكي: {result['reason']}")
        
        return result

# إنشاء المقارن البسيط
simple_comparator = SimpleWorkingComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة البسيطة"""
    
    def simple_compare_and_send():
        """مقارنة بسيطة وإرسال"""
        
        if smart_comparison_enabled[0]:
            try:
                comparison_result = simple_comparator.simple_comparison(
                    item.get('name', ''), new_price, discount_percent
                )
                
                # قبول معظم المنتجات (النظام أكثر تساهلاً)
                if comparison_result['confidence'] < 60:
                    print(f"🚫 رفض نادر: {item.get('name', '')[:35]}... - ثقة ضعيفة")
                    return
                
                # إضافة معلومات المقارنة البسيطة
                item['simple_comparison'] = comparison_result
                item['market_confidence'] = comparison_result['confidence']
                item['market_reason'] = comparison_result['reason']
                item['market_average'] = comparison_result['market_average']
                item['comparison_type'] = comparison_result['comparison_type']
                item['brand'] = comparison_result['brand']
                
                simple_comparator.stats['products_sent'] += 1
                
                print(f"✅ قبول بسيط: {item.get('name', '')[:35]}... - ثقة {comparison_result['confidence']}%")
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة البسيطة: {e}")
                # في حالة الخطأ، نقبل المنتجات مع خصم معقول
                if discount_percent >= 15:
                    item['market_confidence'] = 70
                    item['market_reason'] = f"خصم {discount_percent:.0f}% - قبول احتياطي"
                    item['comparison_type'] = 'error_accept'
                    simple_comparator.stats['products_sent'] += 1
                    print(f"✅ قبول احتياطي: {item.get('name', '')[:35]}...")
                else:
                    return
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=simple_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة والمقارنة البسيطة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة البسيطة
        market_reason = item.get('market_reason', '')
        market_confidence = item.get('market_confidence', 0)
        market_average = item.get('market_average', 0)
        comparison_type = item.get('comparison_type', 'unknown')
        brand = item.get('brand', 'unknown')

        # عرض السعر مع الخصم إذا متوفر
        if old_price and old_price > new_price:
            price_display = f"<s>{int(old_price):,} EGP</s> → <b>{int(new_price):,} EGP</b>"
            discount_info = f"\n⚡ <b>Amazon Discount:</b> <code>{discount_percent:.0f}%</code>"
            savings = old_price - new_price
            savings_info = f"\n💵 <b>You Save:</b> {savings:,.0f} EGP"
        else:
            price_display = f"<b>{int(new_price):,} EGP</b>"
            discount_info = ""
            savings_info = ""

        # عنوان بناءً على نتيجة المقارنة
        if market_confidence >= 85:
            headline = "🔥 <b>AMAZING DEAL!</b> 🔥"
        elif market_confidence >= 80:
            headline = "✅ <b>EXCELLENT DEAL!</b>"
        elif market_confidence >= 75:
            headline = "⚡ <b>GREAT DEAL!</b>"
        else:
            headline = "💸 <b>GOOD DEAL!</b>"

        # معلومات المقارنة
        analysis_info = ""
        if market_reason:
            analysis_info = f"\n🎯 <b>Analysis:</b> {market_reason}"
        
        # متوسط السوق (إذا متوفر)
        market_info = ""
        if market_average > 0:
            market_info = f"\n📊 <b>Market Average:</b> {market_average:,.0f} EGP"
            # حساب نسبة الوفر مقارنة بالسوق
            vs_market = ((market_average - new_price) / market_average) * 100
            if vs_market > 0:
                market_info += f"\n💰 <b>Save vs Market:</b> {vs_market:.0f}%"
        
        # معلومات العلامة التجارية
        brand_info = ""
        if brand and brand != 'unknown':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {market_confidence}%" if market_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 {price_display}{discount_info}{savings_info}{confidence_row}{analysis_info}{market_info}{brand_info}

🔍 <b>Simple Smart Market Analysis</b>
"""

        # أزرار بسيطة وصحيحة
        clean_search = simple_comparator.get_simple_search_term(product_name)
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🌙 Check Noon", "url": f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(clean_search)}"},
                    {"text": "🌐 Search Google", "url": f"https://www.google.com/search?q={urllib.parse.quote(clean_search)}+سعر+مصر"}
                ]
            ]
        }
        reply_markup_json = json.dumps(reply_markup)

        sent_count = 0
        for user_id in users:
            try:
                # إرسال مع الصورة
                if img_url:
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={
                            "chat_id": user_id,
                            "photo": img_url,
                            "caption": msg,
                            "parse_mode": "HTML",
                            "reply_markup": reply_markup_json
                        }, timeout=20
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
            method_text = "مقارنة نون" if comparison_type == 'noon_success' else "قبول ذكي"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - ثقة {market_confidence}% ({method_text})")

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
    """إضافة بيانات التنبيه مع المقارنة البسيطة"""
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
    
    # إرسال مع المقارنة البسيطة
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=15):
    """سكرابة صفحة واحدة مع المقارنة البسيطة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[SIMPLE SMART]" if smart_comparison_enabled[0] else ""
            log_fn(f"🔍 {mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:12]:  # 12 منتج
            try:
                asin = await item.get_attribute("data-asin")
                if not asin:
                    continue

                if auto_new_products_mode[0] and asin in existing_asins:
                    continue

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

                price_el = await item.query_selector('.a-price .a-offscreen')
                if not price_el:
                    continue
                    
                price_txt = await price_el.inner_text()
                price = parse_egp_price(price_txt)
                if not price or price < 40:
                    continue

                # البحث عن السعر المشطوب
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                discount_percent = 0
                
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)
                    if strike_price and strike_price > price:
                        discount_percent = ((strike_price - price) / strike_price) * 100

                # إرسال للمقارنة البسيطة
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
                        strike_price if strike_price else price,
                        price,
                        discount_percent,
                        False
                    )

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
            log_fn(f"[Page {page_num}] 🔍 {new_count} NEW products")
        
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
    
    smart_mode = "SIMPLE SMART ON" if smart_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🔍 Simple Smart Start - New Products: {auto_mode}, Simple Smart: {smart_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Simple smart scraping {sec_name}...", "🔍")
                        for page_num in range(1, pages + 1):
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
                    for page_num in range(1, pages + 1):
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
            log("✅ Simple Smart Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Simple Smart Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    if smart_comparison_enabled[0]:
        stats = simple_comparator.stats
        log(f"🔍 Simple Smart Stats:")
        log(f"   📊 Total Products Processed: {stats['total_products']}")
        log(f"   📱 Products Sent: {stats['products_sent']}")
        log(f"   🌙 Noon Comparisons: {stats['noon_comparisons']}")
        log(f"   🧠 Smart Accepts: {stats['smart_accepts']}")
        
        if stats['noon_comparisons'] > 0:
            avg_market = stats['total_market_value'] / stats['noon_comparisons']
            log(f"   💰 Avg Market Price: {avg_market:,.0f} EGP")
        
        if stats['total_products'] > 0:
            send_rate = (stats['products_sent'] / stats['total_products']) * 100
            comparison_rate = (stats['noon_comparisons'] / stats['total_products']) * 100
            log(f"   📈 Send Rate: {send_rate:.1f}%")
            log(f"   📈 Comparison Rate: {comparison_rate:.1f}%")

def toggle_smart_comparison():
    smart_comparison_enabled[0] = not smart_comparison_enabled[0]
    status = "SIMPLE SMART ON" if smart_comparison_enabled[0] else "OFF"
    log(f"🔍 Simple Smart: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Amazon Price", "Market Average", "Confidence", "Analysis"])
        for asin, item in db.items():
            amazon_price = item.get('price', 0)
            market_avg = item.get('market_average', 0)
            confidence = item.get('market_confidence', 0)
            reason = item.get('market_reason', '')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], amazon_price, market_avg, confidence, reason])
    log("Exported to CSV with simple smart analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# الواجهة الأصلية
root = ctk.CTk()
root.title("LAQTA - Simple Smart Analysis")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Simple Smart Market Analysis", 
                             font=("Arial", 18), text_color="#ffaa44")
subtitle_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")

controls_frame = ctk.CTkFrame(root, fg_color="transparent")
controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
controls_frame.grid_columnconfigure((0,1,2,3,4,5,6,7), weight=1)

section_combo = ctk.CTkComboBox(controls_frame, values=["All Sections"] + list(CATEGORIES.keys()),
    width=170, font=("Arial", 15), button_color="#54fac8")
section_combo.set("Electronics")
section_combo.grid(row=0, column=0, padx=5, pady=8, sticky="ew")

pages_entry = ctk.CTkEntry(controls_frame, width=70, font=("Arial", 15), fg_color="#232d3a", text_color="#12dafb")
pages_entry.insert(0, "3")
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 Auto New", font=("Arial", 13), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

smart_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🔍 Simple Smart", font=("Arial", 13), 
                                      text_color="#4CAF50", command=toggle_smart_comparison)
smart_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
smart_comparison_chk.select()

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

start_btn = ctk.CTkButton(buttons_frame, text="🔍 Simple Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Simple Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#FF9800", hover_color="#e68900", text_color="#ffffff")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#9C27B0", hover_color="#7b1fa2", text_color="#ffffff")
export_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#607D8B", hover_color="#455a64", text_color="#ffffff")
clear_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=300, height=45,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 12))

load_db()

log("🔍 LAQTA Simple Smart Analysis System started!", "🚀")
log("🌙 Noon: Simple HTTP requests for better reliability", "✨")
log("🧠 Smart Accept: Accept good products with trusted brands", "💡")
log("📸 Telegram: ON - with photos and simple smart analysis", "📱")
log("⚡ Speed: No complex async, simple and fast", "🏃")
log("🎯 Strategy: Simple Noon check → Smart brand accept → Send more products", "💪")
log("📱 Expected: WORKING system that sends products with market awareness!", "🏆")

root.mainloop()
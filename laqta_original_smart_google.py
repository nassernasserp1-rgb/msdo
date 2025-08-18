#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - الواجهة الأصلية مع جوجل ذكي محسن
الواجهة الأصلية + بحث جوجل ذكي + إرسال الصور
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
smart_google_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام جوجل الذكي المحسن
class SmartGoogleComparator:
    """نظام جوجل ذكي محسن للواجهة الأصلية"""
    
    def __init__(self):
        self.stats = {
            'total_searches': 0,
            'successful_finds': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'cache_hits': 0,
            'no_results': 0
        }
        self.cache = {}
        
        # قاعدة بيانات الأسعار المرجعية (تقديرية)
        self.price_ranges = {
            # إلكترونيات
            'xiaomi': {'min': 1000, 'max': 8000, 'avg': 3500},
            'samsung': {'min': 2000, 'max': 15000, 'avg': 6000},
            'apple': {'min': 5000, 'max': 50000, 'avg': 20000},
            'iphone': {'min': 15000, 'max': 50000, 'avg': 30000},
            'anker': {'min': 100, 'max': 1500, 'avg': 400},
            'joyroom': {'min': 50, 'max': 800, 'avg': 200},
            'soundcore': {'min': 300, 'max': 3000, 'avg': 1000},
            'canon': {'min': 2000, 'max': 20000, 'avg': 8000},
            'hp': {'min': 3000, 'max': 25000, 'avg': 10000},
            'sony': {'min': 500, 'max': 10000, 'avg': 3000},
            'lg': {'min': 3000, 'max': 30000, 'avg': 12000},
            
            # منتجات التجميل
            'vaseline': {'min': 30, 'max': 200, 'avg': 80},
            'nivea': {'min': 40, 'max': 300, 'avg': 120},
            'dove': {'min': 35, 'max': 250, 'avg': 100},
            'axe': {'min': 50, 'max': 300, 'avg': 150},
            'care': {'min': 25, 'max': 150, 'avg': 60},
            'argento': {'min': 40, 'max': 200, 'avg': 90},
            'loreal': {'min': 80, 'max': 500, 'avg': 200}
        }
    
    def extract_brand_from_name(self, product_name: str) -> str:
        """استخراج العلامة التجارية من اسم المنتج"""
        name_lower = product_name.lower()
        
        for brand in self.price_ranges.keys():
            if brand in name_lower:
                return brand
        
        # إذا لم نجد علامة تجارية معروفة، نأخذ أول كلمة
        first_word = product_name.split()[0].lower() if product_name.split() else ""
        return first_word
    
    def get_smart_price_estimate(self, product_name: str, amazon_price: float) -> dict:
        """تقدير ذكي للأسعار بناءً على العلامة التجارية ونوع المنتج"""
        
        brand = self.extract_brand_from_name(product_name)
        
        # الحصول على النطاق السعري للعلامة التجارية
        if brand in self.price_ranges:
            price_range = self.price_ranges[brand]
            
            # تحديد موقع سعر أمازون في النطاق
            min_price = price_range['min']
            max_price = price_range['max']
            avg_price = price_range['avg']
            
            # حساب تقدير الثقة بناءً على موقع السعر
            if amazon_price <= min_price * 1.2:  # أقل من الحد الأدنى بـ 20%
                confidence = 85
                reason = f"🔥 سعر ممتاز! أقل من المتوقع لـ {brand}"
                is_good = True
            elif amazon_price <= avg_price * 0.8:  # أقل من المتوسط بـ 20%
                confidence = 75
                reason = f"✅ سعر جيد! أقل من متوسط {brand}"
                is_good = True
            elif amazon_price <= avg_price:  # أقل من أو يساوي المتوسط
                confidence = 65
                reason = f"⚡ سعر مقبول! حول متوسط {brand}"
                is_good = True
            elif amazon_price <= avg_price * 1.2:  # أعلى من المتوسط بـ 20%
                confidence = 55
                reason = f"⚠️ سعر مرتفع قليلاً لـ {brand}"
                is_good = True
            else:  # أعلى من المتوسط بكثير
                confidence = 40
                reason = f"❌ سعر مرتفع لـ {brand}"
                is_good = False
            
            return {
                'confidence': confidence,
                'reason': reason,
                'is_good_deal': is_good,
                'estimated_range': f"{min_price:,.0f} - {max_price:,.0f}",
                'estimated_avg': f"{avg_price:,.0f}",
                'brand': brand
            }
        
        else:
            # للعلامات التجارية غير المعروفة، نستخدم تحليل عام
            if amazon_price <= 100:
                confidence = 70
                reason = "⚡ منتج اقتصادي - سعر جيد"
                is_good = True
            elif amazon_price <= 500:
                confidence = 65
                reason = "✅ منتج متوسط السعر"
                is_good = True
            elif amazon_price <= 2000:
                confidence = 60
                reason = "⚠️ منتج متوسط إلى مرتفع"
                is_good = True
            else:
                confidence = 55
                reason = "💰 منتج مرتفع السعر"
                is_good = True
            
            return {
                'confidence': confidence,
                'reason': reason,
                'is_good_deal': is_good,
                'estimated_range': 'غير محدد',
                'estimated_avg': 'غير محدد',
                'brand': 'غير معروف'
            }
    
    async def smart_google_search(self, product_name: str, amazon_price: float) -> dict:
        """بحث ذكي في جوجل مع تقدير الأسعار"""
        
        cache_key = f"smart_{product_name[:20]}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🔍 جوجل ذكي: {product_name[:40]}...")
        
        # تقدير ذكي أولي
        smart_estimate = self.get_smart_price_estimate(product_name, amazon_price)
        
        result = {
            'amazon_price': amazon_price,
            'market_prices': [],
            'market_sites': [],
            'is_good_deal': smart_estimate['is_good_deal'],
            'confidence': smart_estimate['confidence'],
            'reason': smart_estimate['reason'],
            'search_method': 'smart_estimate',
            'brand': smart_estimate['brand']
        }
        
        # محاولة البحث في جوجل (مبسطة)
        try:
            # تبسيط اسم المنتج للبحث
            brand = smart_estimate['brand']
            
            # إنشاء مصطلحات بحث متعددة
            search_terms = []
            
            if brand and brand != 'غير معروف':
                search_terms.append(f"{brand} سعر")
                search_terms.append(f"{brand} price egypt")
            
            # بحث عام مبسط
            simple_words = [w for w in product_name.split()[:3] if len(w) > 3]
            if simple_words:
                search_terms.append(' '.join(simple_words) + " سعر")
            
            # جرب البحث بأول مصطلح فقط (للسرعة)
            if search_terms:
                search_term = search_terms[0]
                
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-images', '--disable-javascript']
                    )
                    
                    context = await browser.new_context()
                    page = await context.new_page()
                    
                    google_url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}&hl=ar&gl=EG"
                    
                    await page.goto(google_url, timeout=8000)
                    await page.wait_for_timeout(2000)
                    
                    # استخراج سريع للأسعار
                    google_data = await page.evaluate("""
                        () => {
                            const bodyText = document.body.innerText || '';
                            const prices = [];
                            const sites = [];
                            
                            // البحث عن أسعار بسيط
                            const priceMatches = bodyText.match(/([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنيه|EGP)/gi);
                            if (priceMatches) {
                                priceMatches.forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9.]/g, ''));
                                    if (price >= 20 && price <= 100000) {
                                        prices.push(price);
                                    }
                                });
                            }
                            
                            // البحث عن مواقع
                            const siteKeywords = ['amazon', 'noon', 'jumia', 'carrefour'];
                            for (const site of siteKeywords) {
                                if (bodyText.toLowerCase().includes(site)) {
                                    sites.push(site);
                                }
                            }
                            
                            return {
                                prices: [...new Set(prices)].sort((a, b) => a - b).slice(0, 8),
                                sites: [...new Set(sites)]
                            };
                        }
                    """)
                    
                    await browser.close()
                    
                    # إذا وجدنا أسعار من جوجل، نحسن التقدير
                    if google_data['prices'] and len(google_data['prices']) >= 2:
                        market_prices = google_data['prices']
                        avg_market = sum(market_prices) / len(market_prices)
                        min_market = min(market_prices)
                        
                        # حساب ترتيب أمازون
                        cheaper_count = sum(1 for p in market_prices if p > amazon_price)
                        amazon_rank = len(market_prices) - cheaper_count + 1
                        
                        # تحسين التقدير بناءً على النتائج الحقيقية
                        if amazon_rank == 1:
                            result['confidence'] = 90
                            result['reason'] = f"🔥 الأرخص من {len(market_prices)} أسعار!"
                        elif amazon_rank == 2:
                            result['confidence'] = 80
                            result['reason'] = f"✅ ثاني أرخص من {len(market_prices)} أسعار"
                        elif amazon_price < avg_market:
                            result['confidence'] = 75
                            result['reason'] = f"⚡ أرخص من المتوسط ({avg_market:,.0f})"
                        else:
                            result['confidence'] = 60
                            result['reason'] = f"⚠️ ترتيب {amazon_rank} من {len(market_prices)}"
                        
                        result['market_prices'] = market_prices
                        result['market_sites'] = google_data['sites']
                        result['search_method'] = 'google_found'
                        result['is_good_deal'] = True
                        
                        print(f"   ✅ جوجل: {len(market_prices)} أسعار، ترتيب {amazon_rank}")
                        self.stats['successful_finds'] += 1
                    
                    else:
                        print(f"   ⚪ جوجل: لم يتم العثور على أسعار")
                        self.stats['no_results'] += 1
        
        except Exception as e:
            print(f"   ⚠️ خطأ في جوجل: {e}")
        
        # إذا لم نجد من جوجل، نعتمد على التقدير الذكي
        if result['search_method'] == 'smart_estimate':
            print(f"   🧠 تقدير ذكي: {result['reason']}")
        
        self.stats['total_searches'] += 1
        self.cache[cache_key] = result
        return result

# إنشاء مقارن جوجل الذكي
smart_google_comparator = SmartGoogleComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة الذكية"""
    
    def smart_google_compare_and_send():
        """مقارنة ذكية وإرسال مع الصورة"""
        
        if smart_google_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    smart_google_comparator.smart_google_search(item.get('name', ''), new_price)
                )
                
                # قبول العروض بثقة 45% فأكثر (أكثر تساهلاً)
                if not comparison_result['is_good_deal'] and comparison_result['confidence'] < 45:
                    print(f"🚫 رفض ذكي: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    smart_google_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة الذكية
                item['google_analysis'] = comparison_result
                item['google_confidence'] = comparison_result['confidence']
                item['google_reason'] = comparison_result['reason']
                item['market_prices'] = comparison_result['market_prices']
                item['market_sites'] = comparison_result['market_sites']
                item['search_method'] = comparison_result['search_method']
                item['brand'] = comparison_result['brand']
                
                smart_google_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة الذكية: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة
                if discount_percent >= 30:
                    item['google_confidence'] = 65
                    item['google_reason'] = "خصم كبير - قبول مباشر"
                    smart_google_comparator.stats['validated_deals'] += 1
                else:
                    return
            finally:
                loop.close()
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=smart_google_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة والمقارنة الذكية"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة الذكية
        google_reason = item.get('google_reason', '')
        google_confidence = item.get('google_confidence', 0)
        market_prices = item.get('market_prices', [])
        market_sites = item.get('market_sites', [])
        search_method = item.get('search_method', 'unknown')
        brand = item.get('brand', '')

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على الثقة
        if google_confidence >= 85:
            headline = "🔥 <b>SMART VERIFIED BEST!</b> 🔥"
        elif google_confidence >= 75:
            headline = "✅ <b>SMART CONFIRMED DEAL!</b>"
        elif google_confidence >= 65:
            headline = "⚡ <b>SMART DEAL FOUND!</b>"
        elif google_confidence >= 55:
            headline = "💸 <b>Deal Alert!</b>"
        else:
            headline = "🛍️ <b>Price Drop!</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # معلومات السوق
        market_info = ""
        if market_prices:
            avg_market = sum(market_prices) / len(market_prices)
            min_market = min(market_prices)
            market_info = f"\n📊 <b>Market:</b> Avg {avg_market:,.0f} | Min {min_market:,.0f}"
        
        # معلومات العلامة التجارية
        brand_info = ""
        if brand and brand != 'غير معروف':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()}"
        
        # معلومات طريقة البحث
        method_info = ""
        if search_method == 'google_found':
            method_info = f"\n🔍 <b>Method:</b> Google Search Results"
        elif search_method == 'smart_estimate':
            method_info = f"\n🧠 <b>Method:</b> Smart Price Estimation"
        
        # معلومات جوجل
        google_info = ""
        if google_reason:
            google_info = f"\n🎯 <b>Smart Analysis:</b> {google_reason}"
        
        if market_sites:
            sites_text = ', '.join(market_sites[:3])
            google_info += f"\n🌐 <b>Sites Found:</b> {sites_text}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {google_confidence}%" if google_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{confidence_row}{market_info}{brand_info}{method_info}{google_info}

🧠 <b>Smart Google Price Analysis</b>
"""

        # أزرار الواجهة الأصلية
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [{"text": "🔍 Google Compare", "url": f"https://www.google.com/search?q={product_name.replace(' ', '+')}&hl=ar&gl=EG"}],
                [{"text": "🛒 Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"}],
                [{"text": "🌙 Noon", "url": f"https://www.noon.com/egypt-en/search/?q={product_name.replace(' ', '+')}"}]
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
            method_text = "جوجل" if search_method == 'google_found' else "تقدير ذكي"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - ثقة {google_confidence}% ({method_text})")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية (نفس الكود الأصلي)
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
    """إضافة بيانات التنبيه مع المقارنة الذكية"""
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
    
    # إرسال مع المقارنة الذكية
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة الأصلية
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة - الطريقة الأصلية"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-images'])
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL أصلي
        url = section_url.format(page_num)
        
        if log_fn:
            google_mode = "[SMART GOOGLE]" if smart_google_enabled[0] else ""
            log_fn(f"🟢 {google_mode} Scraping: {section}, page {page_num}")
        
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
                    
                    if discount_percent >= discount_threshold and discount_percent <= 75 and price >= 30:
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
    
    google_mode = "SMART ON" if smart_google_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🟢 Starting - New Products: {auto_mode}, Smart Google: {google_mode}")
    
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
    
    # إحصائيات جوجل الذكي
    if smart_google_enabled[0]:
        stats = smart_google_comparator.stats
        log(f"🧠 Smart Google Stats:")
        log(f"   📊 Total Searches: {stats['total_searches']}")
        log(f"   ✅ Successful Finds: {stats['successful_finds']}")
        log(f"   📱 Validated Deals: {stats['validated_deals']}")
        log(f"   🚫 Rejected Deals: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ⚪ No Results: {stats['no_results']}")
        
        if stats['total_searches'] > 0:
            find_rate = (stats['successful_finds'] / stats['total_searches']) * 100
            validation_rate = (stats['validated_deals'] / stats['total_searches']) * 100
            log(f"   📈 Google Find Rate: {find_rate:.1f}%")
            log(f"   📈 Validation Rate: {validation_rate:.1f}%")

def toggle_smart_google():
    smart_google_enabled[0] = not smart_google_enabled[0]
    status = "SMART ON" if smart_google_enabled[0] else "OFF"
    log(f"🧠 Smart Google: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price", "Google Confidence", "Brand"])
        for asin, item in db.items():
            google_conf = item.get('google_confidence', 0)
            brand = item.get('brand', 'Unknown')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"], google_conf, brand])
    log("Exported to CSV with smart analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== الواجهة الأصلية ====
root = ctk.CTk()
root.title("LAQTA - Original Interface with Smart Google")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

# العنوان الأصلي
title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper with Smart Google Analysis", 
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

smart_google_chk = ctk.CTkCheckBox(controls_frame, text="🧠 Smart Google", font=("Arial", 13), 
                                  text_color="#4285f4", command=toggle_smart_google)
smart_google_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
smart_google_chk.select()  # مفعل افتراضياً

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

# رسائل ترحيب أصلية
log("🚀 LAQTA started!", "🟢")
log("🧠 Smart Google: ON - intelligent price estimation + Google search", "✨")
log("📸 Telegram: ON - with photos and smart analysis", "📱")
log("🆕 Auto New: OFF - all products", "📦")
log("🎯 Expected: Smart deals with brand-based analysis!", "🏆")

root.mainloop()
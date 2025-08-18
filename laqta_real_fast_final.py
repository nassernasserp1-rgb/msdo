#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النظام الحقيقي والسريع النهائي
الواجهة الأصلية + مقارنة حقيقية سريعة + إرسال الصور
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
real_comparison_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام المقارنة الحقيقية السريعة
class RealFastComparator:
    """مقارن الأسعار الحقيقي والسريع"""
    
    def __init__(self):
        self.stats = {
            'total_comparisons': 0,
            'real_comparisons_found': 0,
            'discount_only_decisions': 0,
            'validated_deals': 0,
            'rejected_deals': 0,
            'cache_hits': 0,
            'avg_comparison_time': 0
        }
        self.cache = {}
        self.last_search_time = 0
        self.min_search_delay = 1.5  # ثانية ونصف بين البحثات للسرعة
        
        # قاعدة بيانات سريعة للعلامات التجارية المعروفة
        self.brand_price_guide = {
            # إلكترونيات (أسعار تقريبية للمقارنة السريعة)
            'xiaomi': 3000, 'samsung': 5000, 'apple': 20000, 'iphone': 25000,
            'anker': 300, 'joyroom': 150, 'sony': 2000, 'lg': 8000,
            'canon': 6000, 'hp': 8000, 'dell': 10000,
            
            # منتجات تجميل وعناية
            'vaseline': 70, 'nivea': 100, 'dove': 80, 'axe': 120,
            'care': 50, 'loreal': 150, 'garnier': 120, 'pantene': 90
        }
    
    def extract_brand_quickly(self, product_name: str) -> str:
        """استخراج سريع للعلامة التجارية"""
        name_lower = product_name.lower()
        
        for brand in self.brand_price_guide.keys():
            if brand in name_lower:
                return brand
        
        return 'unknown'
    
    def quick_price_assessment(self, product_name: str, amazon_price: float, discount_percent: float) -> dict:
        """تقييم سريع للسعر بناءً على الخصم والعلامة التجارية"""
        
        brand = self.extract_brand_quickly(product_name)
        
        result = {
            'is_good_deal': False,
            'confidence': 0,
            'reason': '',
            'assessment_type': 'discount_based',
            'brand': brand
        }
        
        # تقييم أساسي بناءً على نسبة الخصم (سريع وصادق)
        base_confidence = 40
        
        # عامل الخصم (60 نقطة)
        if discount_percent >= 50:
            discount_points = 50
            discount_desc = "خصم ضخم"
        elif discount_percent >= 40:
            discount_points = 40
            discount_desc = "خصم كبير جداً"
        elif discount_percent >= 30:
            discount_points = 30
            discount_desc = "خصم كبير"
        elif discount_percent >= 20:
            discount_points = 20
            discount_desc = "خصم جيد"
        elif discount_percent >= 15:
            discount_points = 15
            discount_desc = "خصم متوسط"
        else:
            discount_points = 5
            discount_desc = "خصم بسيط"
        
        # عامل السعر والعلامة التجارية (40 نقطة)
        brand_points = 0
        if brand != 'unknown' and brand in self.brand_price_guide:
            expected_price = self.brand_price_guide[brand]
            
            if amazon_price <= expected_price * 0.7:  # أقل من المتوقع بـ 30%
                brand_points = 30
                brand_desc = f"سعر ممتاز لـ {brand}"
            elif amazon_price <= expected_price:  # أقل من أو يساوي المتوقع
                brand_points = 20
                brand_desc = f"سعر جيد لـ {brand}"
            elif amazon_price <= expected_price * 1.3:  # أعلى من المتوقع بـ 30%
                brand_points = 10
                brand_desc = f"سعر مقبول لـ {brand}"
            else:  # أعلى من المتوقع بكثير
                brand_points = 0
                brand_desc = f"سعر مرتفع لـ {brand}"
        else:
            # للعلامات غير المعروفة، تقييم عام بناءً على السعر
            if amazon_price <= 100:
                brand_points = 20
                brand_desc = "منتج اقتصادي"
            elif amazon_price <= 500:
                brand_points = 15
                brand_desc = "منتج متوسط السعر"
            elif amazon_price <= 2000:
                brand_points = 10
                brand_desc = "منتج مرتفع السعر"
            else:
                brand_points = 5
                brand_desc = "منتج غالي"
        
        # حساب النقاط النهائية
        total_confidence = base_confidence + discount_points + brand_points
        result['confidence'] = min(100, total_confidence)
        
        # تحديد القبول أو الرفض
        if result['confidence'] >= 70:
            result['is_good_deal'] = True
            result['reason'] = f"✅ {discount_desc} + {brand_desc}"
        elif result['confidence'] >= 60:
            result['is_good_deal'] = True
            result['reason'] = f"⚡ {discount_desc} + {brand_desc}"
        elif result['confidence'] >= 50:
            result['is_good_deal'] = True
            result['reason'] = f"⚠️ {discount_desc} + {brand_desc}"
        else:
            result['is_good_deal'] = False
            result['reason'] = f"❌ {discount_desc} + {brand_desc}"
        
        return result
    
    async def fast_real_comparison(self, product_name: str, amazon_price: float, discount_percent: float) -> dict:
        """مقارنة سريعة وحقيقية"""
        
        # تحكم في السرعة
        current_time = time.time()
        if current_time - self.last_search_time < self.min_search_delay:
            await asyncio.sleep(self.min_search_delay - (current_time - self.last_search_time))
        self.last_search_time = time.time()
        
        cache_key = f"fast_real_{product_name[:15]}_{amazon_price}_{discount_percent}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"⚡ مقارنة سريعة: {product_name[:35]}...")
        
        start_time = time.time()
        
        # تقييم سريع أولي
        quick_result = self.quick_price_assessment(product_name, amazon_price, discount_percent)
        
        # إذا كان الخصم كبير جداً (40%+)، نقبل مباشرة بدون بحث (للسرعة)
        if discount_percent >= 40:
            quick_result['confidence'] = min(90, quick_result['confidence'] + 10)
            quick_result['reason'] += " - خصم كبير مؤكد"
            quick_result['assessment_type'] = 'fast_approval'
            quick_result['is_good_deal'] = True
            
            print(f"   🔥 قبول سريع: خصم {discount_percent:.0f}% - {quick_result['reason']}")
            
            self.stats['discount_only_decisions'] += 1
        
        # إذا كان الخصم متوسط (20-39%)، نحاول بحث سريع (5 ثوانٍ فقط)
        elif 20 <= discount_percent < 40:
            try:
                # بحث سريع جداً في جوميا فقط (الأسرع)
                brand = quick_result['brand']
                search_term = brand if brand != 'unknown' else product_name.split()[0]
                
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-images', '--disable-javascript', '--disable-css']
                    )
                    
                    page = await browser.new_page()
                    
                    # بحث سريع في جوميا فقط
                    jumia_url = f"https://www.jumia.com.eg/catalog/?q={search_term}"
                    
                    await page.goto(jumia_url, timeout=5000)  # 5 ثوانٍ فقط
                    await page.wait_for_timeout(1500)  # انتظار قصير
                    
                    # استخراج سريع للأسعار
                    jumia_prices = await page.evaluate("""
                        () => {
                            const prices = new Set();
                            const bodyText = document.body.innerText || '';
                            
                            // البحث السريع عن الأسعار
                            const priceMatches = bodyText.match(/([0-9,]+)\\s*(?:جنيه|EGP)/gi);
                            if (priceMatches) {
                                priceMatches.forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9]/g, ''));
                                    if (price >= 25 && price <= 50000) {
                                        prices.add(price);
                                    }
                                });
                            }
                            
                            return Array.from(prices).sort((a, b) => a - b).slice(0, 5);
                        }
                    """)
                    
                    await browser.close()
                    
                    if jumia_prices and len(jumia_prices) >= 2:
                        # مقارنة سريعة مع جوميا
                        avg_jumia = sum(jumia_prices) / len(jumia_prices)
                        min_jumia = min(jumia_prices)
                        
                        if amazon_price <= min_jumia:
                            quick_result['confidence'] = 85
                            quick_result['reason'] = f"🔥 أرخص من جوميا! (أقل من {min_jumia:,.0f})"
                            quick_result['assessment_type'] = 'real_comparison_jumia'
                            quick_result['is_good_deal'] = True
                            self.stats['real_comparisons_found'] += 1
                        elif amazon_price <= avg_jumia:
                            quick_result['confidence'] = 75
                            quick_result['reason'] = f"✅ أرخص من متوسط جوميا ({avg_jumia:,.0f})"
                            quick_result['assessment_type'] = 'real_comparison_jumia'
                            quick_result['is_good_deal'] = True
                            self.stats['real_comparisons_found'] += 1
                        else:
                            quick_result['confidence'] = max(50, quick_result['confidence'])
                            quick_result['reason'] += f" (جوميا أرخص: {min_jumia:,.0f})"
                        
                        print(f"   ⚡ جوميا: {len(jumia_prices)} أسعار، أقل {min_jumia:,.0f}")
                    else:
                        print(f"   ⚪ جوميا: لا توجد أسعار")
                        self.stats['discount_only_decisions'] += 1
                
            except Exception as e:
                print(f"   ⚠️ خطأ في البحث السريع: {e}")
                self.stats['discount_only_decisions'] += 1
        
        # إذا كان الخصم صغير (أقل من 20%)، نعتمد على التقييم السريع فقط
        else:
            print(f"   ⚡ تقييم سريع: {quick_result['reason']}")
            self.stats['discount_only_decisions'] += 1
        
        # حساب وقت المقارنة
        comparison_time = time.time() - start_time
        self.stats['avg_comparison_time'] = (
            (self.stats['avg_comparison_time'] * self.stats['total_comparisons'] + comparison_time) / 
            (self.stats['total_comparisons'] + 1)
        )
        
        self.stats['total_comparisons'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = quick_result
        
        return quick_result

# إنشاء مقارن الأسعار السريع والحقيقي
real_fast_comparator = RealFastComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة السريعة والحقيقية"""
    
    def real_fast_compare_and_send():
        """مقارنة سريعة حقيقية وإرسال"""
        
        if real_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    real_fast_comparator.fast_real_comparison(
                        item.get('name', ''), new_price, discount_percent
                    )
                )
                
                # قبول العروض بثقة 50% فأكثر
                if not comparison_result['is_good_deal'] and comparison_result['confidence'] < 50:
                    print(f"🚫 رفض سريع: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    real_fast_comparator.stats['rejected_deals'] += 1
                    return
                
                # إضافة معلومات المقارنة السريعة
                item['real_analysis'] = comparison_result
                item['real_confidence'] = comparison_result['confidence']
                item['real_reason'] = comparison_result['reason']
                item['assessment_type'] = comparison_result['assessment_type']
                item['brand'] = comparison_result['brand']
                
                real_fast_comparator.stats['validated_deals'] += 1
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة السريعة: {e}")
                # في حالة الخطأ، نسمح بالإرسال للعروض الكبيرة
                if discount_percent >= 35:
                    item['real_confidence'] = 70
                    item['real_reason'] = f"خصم كبير {discount_percent:.0f}% - قبول مباشر"
                    real_fast_comparator.stats['validated_deals'] += 1
                else:
                    return
            finally:
                loop.close()
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=real_fast_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة والتحليل الحقيقي"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات التحليل الحقيقي
        real_reason = item.get('real_reason', '')
        real_confidence = item.get('real_confidence', 0)
        assessment_type = item.get('assessment_type', 'unknown')
        brand = item.get('brand', 'unknown')

        price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان صادق بناءً على نسبة الخصم الحقيقية
        if discount_percent >= 50:
            headline = "🔥 <b>HUGE DISCOUNT!</b> 🔥"
        elif discount_percent >= 40:
            headline = "✅ <b>BIG DISCOUNT!</b>"
        elif discount_percent >= 30:
            headline = "⚡ <b>GOOD DISCOUNT!</b>"
        elif discount_percent >= 20:
            headline = "💸 <b>Medium Discount</b>"
        else:
            headline = "🛍️ <b>Small Discount</b>"

        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # حساب المبلغ الموفر
        savings = old_price - new_price if old_price else 0
        savings_info = f"\n💵 <b>You Save:</b> {savings:,.0f} EGP" if savings > 0 else ""
        
        # معلومات العلامة التجارية
        brand_info = ""
        if brand and brand != 'unknown':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()}"
        
        # معلومات طريقة التقييم
        method_info = ""
        if assessment_type == 'real_comparison_jumia':
            method_info = f"\n🔍 <b>Method:</b> Real Jumia Comparison"
        elif assessment_type == 'fast_approval':
            method_info = f"\n⚡ <b>Method:</b> Fast Approval (High Discount)"
        elif assessment_type == 'discount_based':
            method_info = f"\n📊 <b>Method:</b> Discount-Based Analysis"
        
        # معلومات التحليل
        analysis_info = ""
        if real_reason:
            analysis_info = f"\n🎯 <b>Analysis:</b> {real_reason}"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {real_confidence}%" if real_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>{savings_info}{confidence_row}{brand_info}{method_info}{analysis_info}

⚡ <b>Fast & Real Price Analysis</b>
"""

        # أزرار بسيطة وسريعة
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🛒 Check Jumia", "url": f"https://www.jumia.com.eg/catalog/?q={product_name.replace(' ', '+')}"},
                    {"text": "🌙 Check Noon", "url": f"https://www.noon.com/egypt-en/search/?q={product_name.replace(' ', '+')}"}
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
            method_text = "حقيقي" if assessment_type == 'real_comparison_jumia' else "سريع"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - ثقة {real_confidence}% ({method_text})")

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
    """إضافة بيانات التنبيه مع المقارنة السريعة والحقيقية"""
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
    
    # إرسال مع المقارنة السريعة والحقيقية
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة السريعة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة - سريعة ومحسنة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # URL أصلي
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[FAST REAL]" if real_comparison_enabled[0] else ""
            log_fn(f"⚡ {mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)  # انتظار أقل للسرعة
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:12]:  # 12 منتج للتوازن بين السرعة والجودة
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
            log_fn(f"[Page {page_num}] ⚡ {new_count} NEW products")
        
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
    
    real_mode = "FAST REAL ON" if real_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"⚡ Fast Real Start - New Products: {auto_mode}, Fast Real: {real_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Fast Real scraping {sec_name}...", "⚡")
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
            log("✅ Fast Real Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Fast Real Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    # إحصائيات حقيقية
    if real_comparison_enabled[0]:
        stats = real_fast_comparator.stats
        log(f"⚡ Fast Real Stats:")
        log(f"   📊 Total Comparisons: {stats['total_comparisons']}")
        log(f"   🔍 Real Comparisons Found: {stats['real_comparisons_found']}")
        log(f"   📊 Discount-Only Decisions: {stats['discount_only_decisions']}")
        log(f"   📱 Validated Deals: {stats['validated_deals']}")
        log(f"   🚫 Rejected Deals: {stats['rejected_deals']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ⏱️ Avg Comparison Time: {stats['avg_comparison_time']:.1f}s")
        
        if stats['total_comparisons'] > 0:
            real_rate = (stats['real_comparisons_found'] / stats['total_comparisons']) * 100
            validation_rate = (stats['validated_deals'] / stats['total_comparisons']) * 100
            log(f"   📈 Real Comparison Rate: {real_rate:.1f}%")
            log(f"   📈 Validation Rate: {validation_rate:.1f}%")

def toggle_real_comparison():
    real_comparison_enabled[0] = not real_comparison_enabled[0]
    status = "FAST REAL ON" if real_comparison_enabled[0] else "OFF"
    log(f"⚡ Fast Real Comparison: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Last Price", "Discount %", "Confidence", "Analysis Method"])
        for asin, item in db.items():
            discount_pct = item.get('discount_percent', 0)
            confidence = item.get('real_confidence', 0)
            method = item.get('assessment_type', 'unknown')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], item["price"], discount_pct, confidence, method])
    log("Exported to CSV with real analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# ==== الواجهة الأصلية ====
root = ctk.CTk()
root.title("LAQTA - Fast & Real System")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

# العنوان الأصلي
title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Fast & Real Analysis", 
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
pages_entry.insert(0, "3")  # أقل للسرعة
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

# الخيارات الأصلية
auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 Auto New", font=("Arial", 13), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

real_comparison_chk = ctk.CTkCheckBox(controls_frame, text="⚡ Fast Real", font=("Arial", 13), 
                                     text_color="#4CAF50", command=toggle_real_comparison)
real_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
real_comparison_chk.select()  # مفعل افتراضياً

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

start_btn = ctk.CTkButton(buttons_frame, text="⚡ Fast Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Real Stats", command=show_stats, width=btn_w, height=btn_h,
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

# رسائل ترحيب حقيقية وسريعة
log("⚡ LAQTA Fast & Real System started!", "🚀")
log("🔍 Fast Real: ON - real comparisons when possible, smart estimates when not", "✨")
log("📸 Telegram: ON - with photos and honest analysis", "📱")
log("⚡ Speed Priority: 1.5s between searches, 5s timeout for sites", "🏃")
log("🎯 Strategy: 40%+ discount = instant approval, 20-39% = quick Jumia check", "💡")
log("📱 Expected: FAST and REAL verified deals!", "🏆")

root.mainloop()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النظام النهائي المصلح
مقارنة حقيقية مع روابط صحيحة + حل مشاكل البحث
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

ALERT_DISCOUNT = 15  # خفضنا الحد الأدنى للحصول على منتجات أكثر
alerts_data = []
notified_asins = set()
existing_asins = set()

class UltimateSmartComparator:
    """المقارن الذكي النهائي - حل جميع المشاكل"""
    
    def __init__(self):
        self.stats = {
            'total_comparisons': 0,
            'successful_comparisons': 0,
            'noon_successes': 0,
            'accepted_without_comparison': 0,
            'rejected_products': 0,
            'cache_hits': 0,
            'avg_comparison_time': 0,
            'total_market_average': 0
        }
        self.cache = {}
        self.last_search_time = 0
        self.min_search_delay = 4.0  # زيادة التأخير لتجنب الأخطاء
    
    def extract_clean_product_name(self, product_name: str) -> str:
        """استخراج اسم المنتج النظيف للبحث"""
        
        # إزالة الكلمات غير المفيدة
        stop_words = [
            'new', 'original', 'pack', 'set', 'piece', 'amazon', 'choice',
            'brand', 'compatible', 'with', 'for', 'series', 'edition',
            'الجديد', 'أصلي', 'حزمة', 'dual', 'sim', 'inch', 'smart'
        ]
        
        # تنظيف النص
        clean_name = re.sub(r'[^\w\s]', ' ', product_name)
        words = []
        
        for word in clean_name.split():
            clean_word = word.lower().strip()
            if (len(clean_word) > 2 and 
                clean_word not in stop_words and
                not clean_word.isdigit()):
                words.append(clean_word)
            
            if len(words) >= 3:  # أول 3 كلمات مهمة فقط
                break
        
        return ' '.join(words) if words else product_name.split()[0]
    
    def extract_brand(self, product_name: str) -> str:
        """استخراج العلامة التجارية"""
        
        known_brands = [
            'samsung', 'xiaomi', 'apple', 'honor', 'huawei', 'oppo', 'vivo',
            'anker', 'tp-link', 'sony', 'lg', 'wd', 'sandisk', 'logitech',
            'sharp', 'haier', 'jac', 'hikvision', 'joyroom', 'oraimo'
        ]
        
        name_lower = product_name.lower()
        
        # البحث في أول 3 كلمات أولاً
        first_words = product_name.split()[:3]
        for word in first_words:
            clean_word = word.lower().strip()
            if clean_word in known_brands:
                return clean_word
        
        # البحث في النص كله
        for brand in known_brands:
            if brand in name_lower:
                return brand
        
        return 'unknown'
    
    async def search_noon_only(self, search_term: str) -> dict:
        """بحث في نون فقط - مبسط وسريع"""
        
        result = {'prices': [], 'avg_price': 0, 'success': False}
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript', '--disable-css']
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # رابط نون مبسط
                search_url = f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(search_term)}"
                print(f"      🌙 نون: {search_url}")
                
                await page.goto(search_url, timeout=8000)
                await page.wait_for_timeout(3000)
                
                # استخراج بسيط للأسعار
                page_content = await page.content()
                
                # البحث عن الأسعار في محتوى الصفحة
                price_matches = re.findall(r'(\d{2,6})\s*(?:جنيه|EGP)', page_content, re.IGNORECASE)
                
                prices = []
                for match in price_matches:
                    try:
                        price = float(match.replace(',', ''))
                        if 30 <= price <= 100000:  # نطاق منطقي
                            prices.append(price)
                    except:
                        continue
                
                # إزالة التكرار والترتيب
                if prices:
                    unique_prices = sorted(list(set(prices)))
                    
                    # أخذ أول 10 أسعار فقط
                    if len(unique_prices) > 10:
                        unique_prices = unique_prices[:10]
                    
                    result['prices'] = unique_prices
                    result['avg_price'] = statistics.mean(unique_prices)
                    result['success'] = True
                    
                    self.stats['noon_successes'] += 1
                    print(f"         ✅ نجح! {len(unique_prices)} أسعار، متوسط: {result['avg_price']:,.0f} EGP")
                else:
                    print(f"         ⚪ لم يجد أسعار في نون")
                
                await browser.close()
                
        except Exception as e:
            print(f"         ❌ خطأ في نون: {e}")
        
        return result
    
    async def ultimate_comparison(self, product_name: str, amazon_price: float, original_discount: float) -> dict:
        """المقارنة النهائية المحسنة"""
        
        # تحكم في السرعة
        current_time = time.time()
        if current_time - self.last_search_time < self.min_search_delay:
            await asyncio.sleep(self.min_search_delay - (current_time - self.last_search_time))
        self.last_search_time = time.time()
        
        search_term = self.extract_clean_product_name(product_name)
        brand = self.extract_brand(product_name)
        
        cache_key = f"ultimate_{search_term}_{amazon_price}_{brand}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🔍 مقارنة نهائية: {product_name[:40]}...")
        print(f"   🏷️ العلامة: {brand} | 🔎 البحث: '{search_term}'")
        
        start_time = time.time()
        
        result = {
            'amazon_price': amazon_price,
            'market_prices': [],
            'market_average': 0,
            'is_good_deal': True,  # افتراضياً نقبل
            'confidence': 60,
            'reason': 'منتج جيد',
            'comparison_type': 'smart_accept',
            'brand': brand,
            'original_discount': original_discount,
            'comparison_attempted': False
        }
        
        # محاولة البحث في نون فقط (للبساطة والسرعة)
        try:
            noon_result = await asyncio.wait_for(
                self.search_noon_only(search_term), 
                timeout=10
            )
            
            result['comparison_attempted'] = True
            
            if noon_result['success'] and noon_result['prices']:
                # مقارنة ناجحة مع نون
                market_prices = noon_result['prices']
                market_average = noon_result['avg_price']
                
                result['market_prices'] = market_prices
                result['market_average'] = market_average
                self.stats['total_market_average'] += market_average
                
                # حساب موقع أمازون
                vs_average_percent = ((market_average - amazon_price) / market_average) * 100
                min_market = min(market_prices)
                vs_min_percent = ((min_market - amazon_price) / min_market) * 100
                
                if amazon_price <= min_market:
                    result['confidence'] = 95
                    result['reason'] = f"🔥 أرخص من كل السوق! أقل بـ {abs(vs_min_percent):.0f}%"
                elif vs_average_percent > 20:
                    result['confidence'] = 85
                    result['reason'] = f"✅ أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                elif vs_average_percent > 10:
                    result['confidence'] = 80
                    result['reason'] = f"⚡ أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                elif vs_average_percent > 0:
                    result['confidence'] = 75
                    result['reason'] = f"💸 أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                elif vs_average_percent > -15:
                    result['confidence'] = 70
                    result['reason'] = f"⚠️ قريب من متوسط السوق"
                else:
                    result['confidence'] = 60
                    result['reason'] = f"⚠️ أغلى من متوسط السوق بـ {abs(vs_average_percent):.0f}%"
                
                result['comparison_type'] = 'noon_comparison'
                self.stats['successful_comparisons'] += 1
                
                print(f"   📊 مقارنة ناجحة مع نون:")
                print(f"      💰 متوسط السوق: {market_average:,.0f} EGP")
                print(f"      📉 أقل سعر: {min_market:,.0f} EGP")
                print(f"      🎯 أمازون: {amazon_price:,.0f} EGP")
                print(f"   {result['reason']}")
                
            else:
                # لم نجد أسعار في نون - نقبل بناءً على العلامة التجارية والخصم
                result = self.smart_accept_without_comparison(brand, amazon_price, original_discount)
                self.stats['accepted_without_comparison'] += 1
                
        except Exception as e:
            print(f"   ❌ خطأ في البحث: {e}")
            result = self.smart_accept_without_comparison(brand, amazon_price, original_discount)
            self.stats['accepted_without_comparison'] += 1
        
        # حساب وقت المقارنة
        comparison_time = time.time() - start_time
        self.stats['avg_comparison_time'] = (
            (self.stats['avg_comparison_time'] * self.stats['total_comparisons'] + comparison_time) / 
            (self.stats['total_comparisons'] + 1)
        )
        
        self.stats['total_comparisons'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result
    
    def smart_accept_without_comparison(self, brand: str, amazon_price: float, original_discount: float) -> dict:
        """قبول ذكي بدون مقارنة - بناءً على العلامة والخصم"""
        
        result = {
            'amazon_price': amazon_price,
            'market_prices': [],
            'market_average': 0,
            'is_good_deal': True,
            'confidence': 65,
            'reason': 'منتج مقبول',
            'comparison_type': 'smart_accept',
            'brand': brand,
            'original_discount': original_discount,
            'comparison_attempted': False
        }
        
        # تقييم بناءً على العلامة التجارية
        premium_brands = ['samsung', 'apple', 'sony', 'lg', 'anker', 'wd', 'logitech']
        good_brands = ['xiaomi', 'honor', 'huawei', 'tp-link', 'sharp', 'haier']
        budget_brands = ['redmi', 'joyroom', 'oraimo']
        
        if brand in premium_brands:
            result['confidence'] = 80
            result['reason'] = f"✅ علامة ممتازة ({brand}) - قبول مباشر"
        elif brand in good_brands:
            result['confidence'] = 75
            result['reason'] = f"⚡ علامة جيدة ({brand}) - قبول مباشر"
        elif brand in budget_brands:
            result['confidence'] = 70
            result['reason'] = f"💸 علامة اقتصادية ({brand}) - قبول مباشر"
        else:
            # علامة غير معروفة - نعتمد على الخصم
            if original_discount >= 30:
                result['confidence'] = 75
                result['reason'] = f"🔥 خصم كبير {original_discount:.0f}% - قبول"
            elif original_discount >= 20:
                result['confidence'] = 70
                result['reason'] = f"⚡ خصم جيد {original_discount:.0f}% - قبول"
            elif original_discount >= 15:
                result['confidence'] = 65
                result['reason'] = f"💸 خصم متوسط {original_discount:.0f}% - قبول"
            else:
                result['confidence'] = 60
                result['reason'] = f"⚠️ خصم بسيط {original_discount:.0f}% - قبول محدود"
        
        # تعديل بناءً على السعر
        if amazon_price <= 100:
            result['confidence'] += 5
            result['reason'] += " (منتج اقتصادي)"
        elif amazon_price >= 10000:
            result['confidence'] -= 5
            result['reason'] += " (منتج غالي)"
        
        print(f"   🧠 قبول ذكي: {result['reason']} - ثقة {result['confidence']}%")
        
        return result

# إنشاء المقارن النهائي
ultimate_comparator = UltimateSmartComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة النهائية"""
    
    def ultimate_compare_and_send():
        """مقارنة نهائية وإرسال"""
        
        if smart_comparison_enabled[0]:
            # إنشاء loop جديد لتجنب InvalidStateError
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    ultimate_comparator.ultimate_comparison(
                        item.get('name', ''), new_price, discount_percent
                    )
                )
                
                # النظام الجديد أكثر تساهلاً - يرفض فقط الثقة الضعيفة جداً
                if comparison_result['confidence'] < 60:
                    print(f"🚫 رفض نادر: {item.get('name', '')[:35]}... - ثقة ضعيفة جداً")
                    ultimate_comparator.stats['rejected_products'] += 1
                    return
                
                # إضافة معلومات المقارنة النهائية
                item['ultimate_comparison'] = comparison_result
                item['market_confidence'] = comparison_result['confidence']
                item['market_reason'] = comparison_result['reason']
                item['market_average'] = comparison_result['market_average']
                item['comparison_type'] = comparison_result['comparison_type']
                item['brand'] = comparison_result['brand']
                item['comparison_attempted'] = comparison_result['comparison_attempted']
                
                print(f"✅ قبول نهائي: {item.get('name', '')[:35]}... - ثقة {comparison_result['confidence']}%")
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة النهائية: {e}")
                # في حالة الخطأ، نقبل المنتجات الجيدة
                item['market_confidence'] = 65
                item['market_reason'] = f"منتج مقبول - خطأ في المقارنة"
                item['comparison_type'] = 'error_accept'
                print(f"✅ قبول احتياطي: {item.get('name', '')[:35]}...")
            finally:
                # إغلاق آمن للـ loop
                try:
                    if not loop.is_closed():
                        loop.close()
                except:
                    pass
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=ultimate_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة والمقارنة النهائية"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة النهائية
        market_reason = item.get('market_reason', '')
        market_confidence = item.get('market_confidence', 0)
        market_average = item.get('market_average', 0)
        comparison_type = item.get('comparison_type', 'unknown')
        brand = item.get('brand', 'unknown')
        comparison_attempted = item.get('comparison_attempted', False)

        # عرض السعر الحالي فقط
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على نتيجة المقارنة النهائية
        if market_confidence >= 90:
            headline = "🔥 <b>AMAZING DEAL!</b> 🔥"
        elif market_confidence >= 80:
            headline = "✅ <b>EXCELLENT DEAL!</b>"
        elif market_confidence >= 70:
            headline = "⚡ <b>GREAT DEAL!</b>"
        else:
            headline = "💸 <b>GOOD DEAL!</b>"

        # معلومات المقارنة
        market_info = ""
        if market_reason:
            market_info = f"\n🎯 <b>Analysis:</b> {market_reason}"
        
        # متوسط السوق (إذا متوفر)
        market_avg_info = ""
        if market_average > 0:
            market_avg_info = f"\n📊 <b>Market Average:</b> {market_average:,.0f} EGP"
            # حساب نسبة الوفر مقارنة بالسوق
            savings_percent = ((market_average - new_price) / market_average) * 100
            if savings_percent > 0:
                market_avg_info += f"\n💰 <b>You Save vs Market:</b> {savings_percent:.0f}%"
        
        # معلومات العلامة التجارية
        brand_info = ""
        if brand and brand != 'unknown':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()}"
        
        # معلومات نوع التحليل
        method_info = ""
        if comparison_type == 'noon_comparison':
            method_info = f"\n📊 <b>Method:</b> Noon Market Comparison"
        elif comparison_type == 'smart_accept':
            method_info = f"\n📊 <b>Method:</b> Smart Brand Analysis"
        elif comparison_type == 'error_accept':
            method_info = f"\n📊 <b>Method:</b> Safe Accept (Error Fallback)"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {market_confidence}%" if market_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 <b>Amazon Price:</b> {price_now}{confidence_row}{market_info}{market_avg_info}{brand_info}{method_info}

🔍 <b>Ultimate Smart Market Analysis</b>
"""

        # أزرار محسنة مع روابط صحيحة
        clean_search = ultimate_comparator.extract_clean_product_name(product_name)
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🌙 Check Noon", "url": f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(clean_search)}"},
                    {"text": "🌐 Search Web", "url": f"https://www.google.com/search?q={urllib.parse.quote(clean_search)}+سعر+مصر"}
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
            method_text = "مقارنة نون" if comparison_type == 'noon_comparison' else "قبول ذكي"
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
    """إضافة بيانات التنبيه مع المقارنة النهائية"""
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
    
    # إرسال مع المقارنة النهائية
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=15):
    """سكرابة صفحة واحدة مع المقارنة النهائية"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[ULTIMATE SMART]" if smart_comparison_enabled[0] else ""
            log_fn(f"🔍 {mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:8]:  # 8 منتجات للتوازن مع التحليل المتقدم
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
                if not price or price < 50:
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

                # إرسال للمقارنة النهائية (أكثر تساهلاً)
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
    
    smart_mode = "ULTIMATE SMART ON" if smart_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🔍 Ultimate Smart Start - New Products: {auto_mode}, Ultimate: {smart_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Ultimate smart scraping {sec_name}...", "🔍")
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
            log("✅ Ultimate Smart Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Ultimate Smart Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    if smart_comparison_enabled[0]:
        stats = ultimate_comparator.stats
        log(f"🔍 Ultimate Smart Stats:")
        log(f"   📊 Total Comparisons: {stats['total_comparisons']}")
        log(f"   ✅ Successful Comparisons: {stats['successful_comparisons']}")
        log(f"   🧠 Accepted Without Comparison: {stats['accepted_without_comparison']}")
        log(f"   🌙 Noon Successes: {stats['noon_successes']}")
        log(f"   🚫 Rejected Products: {stats['rejected_products']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ⏱️ Avg Comparison Time: {stats['avg_comparison_time']:.1f}s")
        
        if stats['successful_comparisons'] > 0:
            avg_market_price = stats['total_market_average'] / stats['successful_comparisons']
            log(f"   💰 Avg Market Price Found: {avg_market_price:,.0f} EGP")
        
        if stats['total_comparisons'] > 0:
            comparison_rate = (stats['successful_comparisons'] / stats['total_comparisons']) * 100
            acceptance_rate = ((stats['successful_comparisons'] + stats['accepted_without_comparison']) / stats['total_comparisons']) * 100
            noon_rate = (stats['noon_successes'] / stats['total_comparisons']) * 100
            log(f"   📈 Market Comparison Rate: {comparison_rate:.1f}%")
            log(f"   📈 Overall Acceptance Rate: {acceptance_rate:.1f}%")
            log(f"   📈 Noon Success Rate: {noon_rate:.1f}%")

def toggle_smart_comparison():
    smart_comparison_enabled[0] = not smart_comparison_enabled[0]
    status = "ULTIMATE SMART ON" if smart_comparison_enabled[0] else "OFF"
    log(f"🔍 Ultimate Smart: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Amazon Price", "Market Average", "Confidence", "Analysis", "Comparison Type"])
        for asin, item in db.items():
            amazon_price = item.get('price', 0)
            market_avg = item.get('market_average', 0)
            confidence = item.get('market_confidence', 0)
            reason = item.get('market_reason', '')
            comp_type = item.get('comparison_type', '')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], amazon_price, market_avg, confidence, reason, comp_type])
    log("Exported to CSV with ultimate smart analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# الواجهة الأصلية
root = ctk.CTk()
root.title("LAQTA - Ultimate Smart Analysis")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Ultimate Smart Market Analysis", 
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
pages_entry.insert(0, "2")
pages_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

pages_label = ctk.CTkLabel(controls_frame, text="Pages", font=("Arial", 13), text_color="#12dafb")
pages_label.grid(row=0, column=2, padx=5, pady=8, sticky="ew")

auto_new_chk = ctk.CTkCheckBox(controls_frame, text="🆕 Auto New", font=("Arial", 13), 
                              text_color="#ff6666", command=toggle_auto_new_mode)
auto_new_chk.grid(row=0, column=3, padx=5, pady=8, sticky="ew")

smart_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🔍 Ultimate", font=("Arial", 13), 
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

start_btn = ctk.CTkButton(buttons_frame, text="🔍 Ultimate Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Ultimate Stats", command=show_stats, width=btn_w, height=btn_h,
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

log("🔍 LAQTA Ultimate Smart Analysis System started!", "🚀")
log("🌙 Noon Only: Simplified and reliable market comparison", "✨")
log("🧠 Smart Fallback: Accept good products even without comparison", "💡")
log("📸 Telegram: ON - with photos and smart analysis", "📱")
log("⚡ Speed: 4s between searches, fixed asyncio errors", "🏃")
log("🎯 Strategy: Try Noon comparison → Smart brand analysis → Accept good deals", "💪")
log("📱 Expected: MORE products sent with flexible but smart quality control!", "🏆")

root.mainloop()
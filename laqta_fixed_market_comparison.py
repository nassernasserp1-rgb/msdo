#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - مقارنة السوق المصري المحسنة والمصلحة
إصلاح مشاكل الرفض والأخطاء + نظام مرن للقبول
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
market_comparison_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

# نظام مقارنة السوق المصري المحسن
class FlexibleMarketComparator:
    """مقارن السوق المصري المرن - يقبل المنتجات حتى لو مفيش مقارنة"""
    
    def __init__(self):
        self.stats = {
            'total_comparisons': 0,
            'successful_market_comparisons': 0,
            'fallback_decisions': 0,
            'noon_successes': 0,
            'comparison_errors': 0,
            'cache_hits': 0,
            'avg_comparison_time': 0
        }
        self.cache = {}
        self.last_search_time = 0
        self.min_search_delay = 3.0  # 3 ثوانٍ بين البحثات
        
        # قاعدة بيانات العلامات التجارية للتقييم السريع
        self.brand_guide = {
            # علامات مشهورة - تستحق الإرسال حتى لو مفيش مقارنة
            'samsung': {'quality': 'premium', 'min_price': 500, 'max_price': 50000},
            'xiaomi': {'quality': 'good', 'min_price': 300, 'max_price': 15000},
            'anker': {'quality': 'premium', 'min_price': 100, 'max_price': 2000},
            'apple': {'quality': 'premium', 'min_price': 5000, 'max_price': 100000},
            'sony': {'quality': 'premium', 'min_price': 500, 'max_price': 30000},
            'lg': {'quality': 'premium', 'min_price': 1000, 'max_price': 50000},
            'tp-link': {'quality': 'good', 'min_price': 200, 'max_price': 5000},
            'wd': {'quality': 'premium', 'min_price': 500, 'max_price': 10000},
            'haier': {'quality': 'good', 'min_price': 2000, 'max_price': 30000},
            'redmi': {'quality': 'budget', 'min_price': 200, 'max_price': 8000},
            'joyroom': {'quality': 'budget', 'min_price': 50, 'max_price': 500},
            'soundcore': {'quality': 'good', 'min_price': 200, 'max_price': 3000},
        }
    
    def extract_brand_from_name(self, product_name: str) -> str:
        """استخراج العلامة التجارية من اسم المنتج"""
        name_lower = product_name.lower()
        
        # البحث عن العلامة التجارية
        for brand in self.brand_guide.keys():
            if brand in name_lower:
                return brand
        
        return 'unknown'
    
    def extract_search_keywords(self, product_name: str) -> str:
        """استخراج كلمات البحث المحسنة"""
        
        # إزالة الكلمات غير المفيدة
        stop_words = [
            'new', 'original', 'pack', 'set', 'piece', 'amazon', 'choice',
            'brand', 'compatible', 'with', 'for', 'series', 'edition',
            'الجديد', 'أصلي', 'حزمة', 'dual', 'sim'
        ]
        
        # استخراج الكلمات المهمة
        words = []
        product_words = re.findall(r'\b[a-zA-Z]{2,}\b', product_name)
        
        for word in product_words[:6]:  # أول 6 كلمات
            clean_word = word.lower()
            if len(clean_word) > 2 and clean_word not in stop_words:
                words.append(clean_word)
        
        return ' '.join(words[:3]) if words else product_name.split()[0]
    
    async def quick_noon_search(self, search_term: str) -> list:
        """بحث سريع في نون فقط (أسرع وأكثر موثوقية)"""
        prices = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript', '--disable-css']
                )
                
                page = await browser.new_page()
                
                # رابط نون مبسط
                noon_url = f"https://www.noon.com/egypt-en/search/?q={search_term.replace(' ', '%20')}"
                
                try:
                    await page.goto(noon_url, timeout=6000)
                    await page.wait_for_timeout(2000)
                    
                    # استخراج أسرع للأسعار
                    noon_prices = await page.evaluate("""
                        () => {
                            const prices = new Set();
                            const bodyText = document.body.innerText || '';
                            
                            // البحث السريع في النص
                            const matches = bodyText.match(/([0-9,]+)\\s*(?:جنيه|EGP)/gi);
                            if (matches) {
                                matches.slice(0, 15).forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9]/g, ''));
                                    if (price >= 20 && price <= 100000) {
                                        prices.add(price);
                                    }
                                });
                            }
                            
                            return Array.from(prices).sort((a, b) => a - b).slice(0, 10);
                        }
                    """)
                    
                    if noon_prices and len(noon_prices) > 0:
                        prices = noon_prices
                        self.stats['noon_successes'] += 1
                        print(f"      🌙 نون: {len(prices)} أسعار - من {min(prices):,.0f} إلى {max(prices):,.0f}")
                    
                except Exception as e:
                    print(f"      ⚠️ نون: خطأ في التحميل - {e}")
                
                await browser.close()
                
        except Exception as e:
            print(f"      ❌ نون: خطأ عام - {e}")
            self.stats['comparison_errors'] += 1
        
        return prices
    
    async def flexible_market_comparison(self, product_name: str, amazon_price: float, original_discount: float) -> dict:
        """مقارنة مرنة - تقبل المنتجات حتى لو مفيش مقارنة"""
        
        # تحكم في السرعة
        current_time = time.time()
        if current_time - self.last_search_time < self.min_search_delay:
            await asyncio.sleep(self.min_search_delay - (current_time - self.last_search_time))
        self.last_search_time = time.time()
        
        search_term = self.extract_search_keywords(product_name)
        brand = self.extract_brand_from_name(product_name)
        
        cache_key = f"flexible_{search_term}_{amazon_price}_{brand}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🏪 مقارنة مرنة: {product_name[:40]}...")
        print(f"   🔎 كلمات البحث: '{search_term}' | 🏷️ العلامة: {brand}")
        
        start_time = time.time()
        
        result = {
            'amazon_price': amazon_price,
            'market_prices': [],
            'market_average': 0,
            'is_good_deal': True,  # افتراضياً نقبل
            'confidence': 60,      # ثقة متوسطة افتراضياً
            'reason': 'منتج جيد',
            'comparison_type': 'fallback_accept',
            'brand': brand,
            'original_discount': original_discount
        }
        
        # محاولة البحث السريع في نون فقط
        try:
            noon_prices = await asyncio.wait_for(
                self.quick_noon_search(search_term), 
                timeout=8
            )
            
            if noon_prices and len(noon_prices) >= 2:
                # مقارنة ناجحة مع نون
                market_average = statistics.mean(noon_prices)
                market_min = min(noon_prices)
                
                result['market_prices'] = noon_prices
                result['market_average'] = market_average
                
                # حساب موقع أمازون
                vs_average_percent = ((market_average - amazon_price) / market_average) * 100
                vs_min_percent = ((market_min - amazon_price) / market_min) * 100
                
                if amazon_price <= market_min:
                    result['confidence'] = 95
                    result['reason'] = f"🔥 أرخص من نون! أقل بـ {abs(vs_min_percent):.0f}%"
                elif vs_average_percent > 20:
                    result['confidence'] = 85
                    result['reason'] = f"✅ أرخص بـ {vs_average_percent:.0f}% من متوسط نون"
                elif vs_average_percent > 10:
                    result['confidence'] = 75
                    result['reason'] = f"⚡ أرخص بـ {vs_average_percent:.0f}% من متوسط نون"
                elif vs_average_percent > 0:
                    result['confidence'] = 70
                    result['reason'] = f"💸 أرخص بـ {vs_average_percent:.0f}% من متوسط نون"
                else:
                    result['confidence'] = 60
                    result['reason'] = f"⚠️ قريب من متوسط نون ({market_average:,.0f})"
                
                result['comparison_type'] = 'noon_comparison'
                self.stats['successful_market_comparisons'] += 1
                
                print(f"   📊 مقارنة ناجحة مع نون:")
                print(f"      💰 متوسط نون: {market_average:,.0f} EGP")
                print(f"      🎯 أمازون: {amazon_price:,.0f} EGP")
                print(f"   {result['reason']}")
                
            else:
                # لم نجد أسعار في نون - نستخدم التقييم الذكي
                result = self.smart_fallback_decision(product_name, amazon_price, brand, original_discount)
                self.stats['fallback_decisions'] += 1
                
        except asyncio.TimeoutError:
            print(f"   ⏱️ انتهت مهلة البحث - استخدام التقييم الذكي")
            result = self.smart_fallback_decision(product_name, amazon_price, brand, original_discount)
            self.stats['fallback_decisions'] += 1
            
        except Exception as e:
            print(f"   ❌ خطأ في البحث - استخدام التقييم الذكي: {e}")
            result = self.smart_fallback_decision(product_name, amazon_price, brand, original_discount)
            self.stats['fallback_decisions'] += 1
            self.stats['comparison_errors'] += 1
        
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
    
    def smart_fallback_decision(self, product_name: str, amazon_price: float, brand: str, original_discount: float) -> dict:
        """قرار ذكي عند عدم وجود مقارنة - يقبل المنتجات الجيدة"""
        
        result = {
            'amazon_price': amazon_price,
            'market_prices': [],
            'market_average': 0,
            'is_good_deal': True,
            'confidence': 60,
            'reason': 'منتج جيد',
            'comparison_type': 'smart_fallback',
            'brand': brand,
            'original_discount': original_discount
        }
        
        # تقييم بناءً على العلامة التجارية
        if brand in self.brand_guide:
            brand_info = self.brand_guide[brand]
            quality = brand_info['quality']
            min_price = brand_info['min_price']
            max_price = brand_info['max_price']
            
            # تقييم السعر بناءً على العلامة التجارية
            if min_price <= amazon_price <= max_price:
                if quality == 'premium':
                    result['confidence'] = 80
                    result['reason'] = f"✅ علامة ممتازة ({brand}) بسعر مناسب"
                elif quality == 'good':
                    result['confidence'] = 75
                    result['reason'] = f"⚡ علامة جيدة ({brand}) بسعر مناسب"
                else:  # budget
                    result['confidence'] = 70
                    result['reason'] = f"💸 علامة اقتصادية ({brand}) بسعر مناسب"
            else:
                result['confidence'] = 65
                result['reason'] = f"⚠️ علامة معروفة ({brand}) - سعر خارج النطاق المعتاد"
        
        else:
            # علامة غير معروفة - نعتمد على الخصم الأصلي
            if original_discount >= 40:
                result['confidence'] = 75
                result['reason'] = f"🔥 خصم كبير {original_discount:.0f}% (علامة غير معروفة)"
            elif original_discount >= 25:
                result['confidence'] = 70
                result['reason'] = f"⚡ خصم جيد {original_discount:.0f}% (علامة غير معروفة)"
            elif original_discount >= 15:
                result['confidence'] = 65
                result['reason'] = f"💸 خصم متوسط {original_discount:.0f}% (علامة غير معروفة)"
            else:
                result['confidence'] = 60
                result['reason'] = f"⚠️ علامة غير معروفة - خصم بسيط {original_discount:.0f}%"
        
        # تعديل بناءً على السعر العام
        if amazon_price <= 100:
            result['confidence'] += 5  # المنتجات الرخيصة أقل مخاطرة
            result['reason'] += " (منتج اقتصادي)"
        elif amazon_price >= 5000:
            result['confidence'] -= 5  # المنتجات الغالية تحتاج حذر أكثر
            result['reason'] += " (منتج غالي)"
        
        # ضمان الحد الأدنى للثقة
        result['confidence'] = max(55, min(90, result['confidence']))
        
        print(f"   🧠 تقييم ذكي: {result['reason']} - ثقة {result['confidence']}%")
        
        return result

# إنشاء مقارن السوق المرن
flexible_comparator = FlexibleMarketComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة المرنة"""
    
    def flexible_compare_and_send():
        """مقارنة مرنة وإرسال"""
        
        if market_comparison_enabled[0]:
            # استخدام asyncio بطريقة آمنة
            try:
                # إنشاء loop جديد للتجنب InvalidStateError
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                comparison_result = loop.run_until_complete(
                    flexible_comparator.flexible_market_comparison(
                        item.get('name', ''), new_price, discount_percent
                    )
                )
                
                # النظام المرن يقبل معظم المنتجات
                if comparison_result['confidence'] < 55:  # رفض فقط الثقة الضعيفة جداً
                    print(f"🚫 رفض نادر: {item.get('name', '')[:35]}... - ثقة ضعيفة جداً")
                    return
                
                # إضافة معلومات المقارنة المرنة
                item['flexible_comparison'] = comparison_result
                item['market_confidence'] = comparison_result['confidence']
                item['market_reason'] = comparison_result['reason']
                item['market_average'] = comparison_result['market_average']
                item['comparison_type'] = comparison_result['comparison_type']
                item['brand'] = comparison_result['brand']
                
                print(f"✅ قبول مرن: {item.get('name', '')[:35]}... - ثقة {comparison_result['confidence']}%")
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة المرنة: {e}")
                # في حالة الخطأ، نقبل المنتجات مع الخصم الجيد
                if discount_percent >= 20:
                    item['market_confidence'] = 65
                    item['market_reason'] = f"خصم جيد {discount_percent:.0f}% - قبول احتياطي"
                    item['comparison_type'] = 'error_fallback'
                    print(f"✅ قبول احتياطي: {item.get('name', '')[:35]}... - خصم {discount_percent:.0f}%")
                else:
                    print(f"🚫 رفض بسبب خطأ: {item.get('name', '')[:35]}...")
                    return
            finally:
                # إغلاق الـ loop بأمان
                try:
                    loop.close()
                except:
                    pass
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=flexible_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة ونتائج المقارنة المرنة"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات المقارنة المرنة
        market_reason = item.get('market_reason', '')
        market_confidence = item.get('market_confidence', 0)
        market_average = item.get('market_average', 0)
        comparison_type = item.get('comparison_type', 'unknown')
        brand = item.get('brand', 'unknown')

        # عرض السعر الحالي فقط
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على نتيجة المقارنة المرنة
        if market_confidence >= 85:
            headline = "🔥 <b>EXCELLENT DEAL!</b> 🔥"
        elif market_confidence >= 75:
            headline = "✅ <b>GREAT DEAL!</b>"
        elif market_confidence >= 65:
            headline = "⚡ <b>GOOD DEAL!</b>"
        else:
            headline = "💸 <b>Fair Deal</b>"

        # معلومات المقارنة
        market_info = ""
        if market_reason:
            market_info = f"\n🎯 <b>Analysis:</b> {market_reason}"
        
        # متوسط السوق (إذا متوفر)
        market_avg_info = ""
        if market_average > 0:
            market_avg_info = f"\n📊 <b>Market Average:</b> {market_average:,.0f} EGP"
        
        # معلومات العلامة التجارية
        brand_info = ""
        if brand and brand != 'unknown':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()}"
        
        # معلومات نوع التحليل
        method_info = ""
        if comparison_type == 'noon_comparison':
            method_info = f"\n📊 <b>Method:</b> Noon Market Comparison"
        elif comparison_type == 'smart_fallback':
            method_info = f"\n📊 <b>Method:</b> Smart Brand Analysis"
        elif comparison_type == 'error_fallback':
            method_info = f"\n📊 <b>Method:</b> Discount-Based (Backup)"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {market_confidence}%" if market_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 <b>Amazon Price:</b> {price_now}{confidence_row}{market_info}{market_avg_info}{brand_info}{method_info}

🏪 <b>Flexible Egyptian Market Analysis</b>
"""

        # أزرار محسنة
        search_keywords = flexible_comparator.extract_search_keywords(product_name)
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🌙 Check Noon", "url": f"https://www.noon.com/egypt-en/search/?q={search_keywords.replace(' ', '%20')}"},
                    {"text": "🌐 Search Web", "url": f"https://www.google.com/search?q={search_keywords.replace(' ', '+')}+سعر+مصر"}
                ],
                [{"text": "🏪 كان بكام", "url": f"https://www.kanbkam.com/search?q={search_keywords.replace(' ', '+')}"}]
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
            method_text = "مقارنة نون" if comparison_type == 'noon_comparison' else "تحليل ذكي"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - ثقة {market_confidence}% ({method_text})")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية (نفس الكود السابق مع تعديلات بسيطة)
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
    """إضافة بيانات التنبيه مع المقارنة المرنة"""
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
    
    # إرسال مع المقارنة المرنة
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة مع المقارنة المرنة"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[FLEXIBLE MARKET]" if market_comparison_enabled[0] else ""
            log_fn(f"🏪 {mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:12]:  # 12 منتج للتوازن
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
                if not price or price < 30:  # رفع الحد الأدنى قليلاً
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

                # إرسال للمقارنة المرنة (النظام الجديد أكثر تساهلاً)
                if discount_alert_cb and price >= 30:
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
            log_fn(f"[Page {page_num}] 🏪 {new_count} NEW products")
        
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
    
    market_mode = "FLEXIBLE MARKET ON" if market_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🏪 Flexible Market Start - New Products: {auto_mode}, Flexible: {market_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Flexible market scraping {sec_name}...", "🏪")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🏪"),
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
                            log_fn=lambda m: log(m, "🏪"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Flexible Market Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Flexible Market Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    if market_comparison_enabled[0]:
        stats = flexible_comparator.stats
        log(f"🏪 Flexible Market Stats:")
        log(f"   📊 Total Comparisons: {stats['total_comparisons']}")
        log(f"   ✅ Successful Market Comparisons: {stats['successful_market_comparisons']}")
        log(f"   🧠 Fallback Decisions: {stats['fallback_decisions']}")
        log(f"   🌙 Noon Successes: {stats['noon_successes']}")
        log(f"   ❌ Comparison Errors: {stats['comparison_errors']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ⏱️ Avg Comparison Time: {stats['avg_comparison_time']:.1f}s")
        
        if stats['total_comparisons'] > 0:
            market_rate = (stats['successful_market_comparisons'] / stats['total_comparisons']) * 100
            fallback_rate = (stats['fallback_decisions'] / stats['total_comparisons']) * 100
            noon_rate = (stats['noon_successes'] / stats['total_comparisons']) * 100
            log(f"   📈 Market Comparison Rate: {market_rate:.1f}%")
            log(f"   📈 Fallback Rate: {fallback_rate:.1f}%")
            log(f"   📈 Noon Success Rate: {noon_rate:.1f}%")

def toggle_market_comparison():
    market_comparison_enabled[0] = not market_comparison_enabled[0]
    status = "FLEXIBLE MARKET ON" if market_comparison_enabled[0] else "OFF"
    log(f"🏪 Flexible Market: {status}")

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
    log("Exported to CSV with flexible market analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# الواجهة الأصلية
root = ctk.CTk()
root.title("LAQTA - Flexible Market Analysis")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Flexible Market Analysis", 
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

market_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🏪 Flexible Market", font=("Arial", 13), 
                                       text_color="#4CAF50", command=toggle_market_comparison)
market_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
market_comparison_chk.select()

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

start_btn = ctk.CTkButton(buttons_frame, text="🏪 Flexible Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Flexible Stats", command=show_stats, width=btn_w, height=btn_h,
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

log("🏪 LAQTA Flexible Market Analysis System started!", "🚀")
log("🌙 Noon + Smart Fallback: Flexible market comparison with brand analysis", "✨")
log("📸 Telegram: ON - with photos and flexible analysis", "📱")
log("⚡ Speed: 3s between searches, 6s timeout, smart caching", "🏃")
log("🎯 Strategy: Try market comparison, fall back to smart brand analysis", "💡")
log("📱 Expected: MORE products sent with flexible quality control!", "🏆")

root.mainloop()
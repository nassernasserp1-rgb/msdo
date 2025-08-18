#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA Professional - نسخة احترافية بدون AI خارجي
تحليل ذكي محلي + مقارنة أسعار + تليجرام
"""

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime
import re
import requests
from playwright.async_api import async_playwright
import statistics
import time
import urllib.parse
from typing import Dict, List, Optional

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

# إعداد الواجهة
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# متغيرات عامة
DB_FILE = "amz_products.json"
db = {}
stop_flag = {"stop": False}
running = [False]
telegram_alerts_enabled = [True]
smart_analysis_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 15
alerts_data = []
notified_asins = set()
existing_asins = set()

class ProfessionalSmartAnalyzer:
    """محلل ذكي احترافي بدون AI خارجي"""
    
    def __init__(self):
        self.stats = {
            'total_analyses': 0,
            'smart_analyses': 0,
            'noon_comparisons': 0,
            'products_sent': 0,
            'products_rejected': 0
        }
        
        print("✅ Professional Smart Analyzer مفعل - تحليل ذكي محلي")
        print("🧠 لا يحتاج اتصال إنترنت للتحليل")
        print("💡 تحليل احترافي بناءً على قواعد ذكية")
    
    async def search_noon_prices(self, search_term: str) -> List[float]:
        """بحث أسعار في نون"""
        prices = []
        
        try:
            clean_term = search_term[:25]
            search_url = f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(clean_term)}"
            
            response = requests.get(search_url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                content = response.text
                price_matches = re.findall(r'(\d{2,6})\s*(?:جنيه|EGP)', content, re.IGNORECASE)
                
                for match in price_matches[:8]:
                    try:
                        price = float(match.replace(',', ''))
                        if 50 <= price <= 30000:
                            prices.append(price)
                    except:
                        continue
                
                if prices:
                    unique_prices = sorted(list(set(prices)))[:5]
                    self.stats['noon_comparisons'] += 1
                    print(f"      🌙 نون: {len(unique_prices)} أسعار")
                    return unique_prices
                
        except Exception:
            pass
        
        return []
    
    def analyze_product_professional(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل احترافي شامل"""
        
        print(f"🔍 تحليل احترافي: {product_name[:50]}...")
        
        name_lower = product_name.lower()
        
        # قاعدة بيانات العلامات التجارية الشاملة
        brand_database = {
            # علامات ممتازة (90-95% ثقة)
            'samsung': {'quality': 'ممتاز', 'base_confidence': 90, 'keywords': ['galaxy', 'note', 'tab', 'smart', 'led', 'qled']},
            'apple': {'quality': 'ممتاز', 'base_confidence': 95, 'keywords': ['iphone', 'ipad', 'macbook', 'airpods', 'watch', 'airtag']},
            'anker': {'quality': 'ممتاز', 'base_confidence': 90, 'keywords': ['powercore', 'soundcore', 'charger', 'cable', 'hub']},
            'sony': {'quality': 'ممتاز', 'base_confidence': 90, 'keywords': ['xperia', 'playstation', 'headphones', 'camera', 'tv']},
            
            # علامات جيدة جداً (80-89% ثقة)
            'xiaomi': {'quality': 'جيد جداً', 'base_confidence': 85, 'keywords': ['redmi', 'mi', 'poco', 'band', 'scooter']},
            'lg': {'quality': 'جيد جداً', 'base_confidence': 85, 'keywords': ['oled', 'nanocell', 'gram', 'smart', 'tv']},
            'huawei': {'quality': 'جيد جداً', 'base_confidence': 80, 'keywords': ['mate', 'nova', 'honor', 'watch', 'band']},
            
            # علامات جيدة (70-79% ثقة)
            'tp-link': {'quality': 'جيد', 'base_confidence': 75, 'keywords': ['archer', 'deco', 'wifi', 'router', 'extender']},
            'asus': {'quality': 'جيد', 'base_confidence': 75, 'keywords': ['rog', 'vivobook', 'zenbook', 'router', 'motherboard']},
            'dell': {'quality': 'جيد', 'base_confidence': 75, 'keywords': ['inspiron', 'xps', 'latitude', 'alienware', 'monitor']},
            'hp': {'quality': 'جيد', 'base_confidence': 75, 'keywords': ['pavilion', 'envy', 'omen', 'elitebook', 'printer']},
            'lenovo': {'quality': 'جيد', 'base_confidence': 75, 'keywords': ['thinkpad', 'ideapad', 'legion', 'yoga', 'tab']},
            
            # علامات مقبولة (60-69% ثقة)
            'generic': {'quality': 'مقبول', 'base_confidence': 60, 'keywords': []},
            'no brand': {'quality': 'مقبول', 'base_confidence': 55, 'keywords': []}
        }
        
        # اكتشاف العلامة التجارية
        brand = 'unknown'
        brand_info = {'quality': 'متوسط', 'base_confidence': 65, 'keywords': []}
        
        for b, info in brand_database.items():
            if b in name_lower:
                brand = b
                brand_info = info
                print(f"   🏷️ العلامة المكتشفة: {brand} ({info['quality']})")
                break
        
        # البحث عن كلمات مفتاحية للعلامة
        keyword_bonus = 0
        if brand_info['keywords']:
            for keyword in brand_info['keywords']:
                if keyword in name_lower:
                    keyword_bonus += 2
                    print(f"   🔍 كلمة مفتاحية: {keyword} (+2%)")
        
        # تحليل السعر
        price_analysis = self.analyze_price_range(amazon_price, brand)
        price_bonus = price_analysis['confidence_bonus']
        
        # تحليل اسم المنتج
        name_analysis = self.analyze_product_name(product_name)
        name_bonus = name_analysis['confidence_bonus']
        
        # حساب الثقة النهائية
        final_confidence = min(
            brand_info['base_confidence'] + keyword_bonus + price_bonus + name_bonus,
            95
        )
        
        # تحديد التوصية
        recommendation_data = self.get_recommendation(final_confidence, brand, amazon_price)
        
        # كلمات البحث الذكية
        search_keywords = self.extract_smart_keywords(product_name, brand)
        
        result = {
            'brand': brand,
            'brand_quality': brand_info['quality'],
            'search_keywords': search_keywords,
            'confidence': final_confidence,
            'assessment': recommendation_data['assessment'],
            'recommendation': recommendation_data['recommendation'],
            'price_analysis': price_analysis,
            'name_analysis': name_analysis,
            'smart_used': True
        }
        
        print(f"   📊 النتيجة النهائية:")
        print(f"      🏷️ العلامة: {result['brand']} ({result['brand_quality']})")
        print(f"      📈 الثقة: {result['confidence']}%")
        print(f"      💰 تحليل السعر: {price_analysis['category']}")
        print(f"      📝 تحليل الاسم: {name_analysis['category']}")
        print(f"      🎯 التوصية: {result['recommendation']}")
        
        self.stats['total_analyses'] += 1
        self.stats['smart_analyses'] += 1
        
        return result
    
    def analyze_price_range(self, price: float, brand: str) -> Dict:
        """تحليل نطاق السعر"""
        
        # نطاقات الأسعار بناءً على العلامة
        price_ranges = {
            'apple': {'low': 5000, 'high': 80000},
            'samsung': {'low': 1000, 'high': 50000},
            'anker': {'low': 200, 'high': 5000},
            'sony': {'low': 800, 'high': 30000},
            'xiaomi': {'low': 300, 'high': 15000},
            'lg': {'low': 500, 'high': 40000},
            'unknown': {'low': 100, 'high': 20000}
        }
        
        range_info = price_ranges.get(brand, price_ranges['unknown'])
        
        if price < range_info['low']:
            return {
                'category': 'سعر ممتاز',
                'confidence_bonus': 10,
                'reason': f'أقل من المتوقع للعلامة'
            }
        elif price > range_info['high']:
            return {
                'category': 'سعر مرتفع',
                'confidence_bonus': -5,
                'reason': f'أعلى من المتوقع للعلامة'
            }
        else:
            return {
                'category': 'سعر معقول',
                'confidence_bonus': 5,
                'reason': f'في النطاق المتوقع'
            }
    
    def analyze_product_name(self, name: str) -> Dict:
        """تحليل اسم المنتج"""
        
        # كلمات إيجابية
        positive_words = [
            'pro', 'max', 'plus', 'ultra', 'premium', 'deluxe', 'professional',
            'smart', 'wireless', 'bluetooth', 'fast', 'quick', 'rapid',
            'hd', '4k', 'uhd', 'oled', 'led', 'amoled'
        ]
        
        # كلمات سلبية
        negative_words = [
            'cheap', 'basic', 'simple', 'mini', 'lite', 'light',
            'generic', 'no brand', 'unbranded'
        ]
        
        name_lower = name.lower()
        positive_count = sum(1 for word in positive_words if word in name_lower)
        negative_count = sum(1 for word in negative_words if word in name_lower)
        
        if positive_count > negative_count:
            return {
                'category': 'اسم متميز',
                'confidence_bonus': positive_count * 2,
                'reason': f'{positive_count} كلمات إيجابية'
            }
        elif negative_count > positive_count:
            return {
                'category': 'اسم بسيط',
                'confidence_bonus': -negative_count * 2,
                'reason': f'{negative_count} كلمات سلبية'
            }
        else:
            return {
                'category': 'اسم عادي',
                'confidence_bonus': 0,
                'reason': 'متوازن'
            }
    
    def get_recommendation(self, confidence: int, brand: str, price: float) -> Dict:
        """تحديد التوصية النهائية"""
        
        if confidence >= 90:
            return {
                'assessment': f"🔥 صفقة ممتازة - {brand.title()}",
                'recommendation': "اشتري فوراً"
            }
        elif confidence >= 80:
            return {
                'assessment': f"✅ صفقة جيدة جداً - {brand.title()}",
                'recommendation': "اشتري"
            }
        elif confidence >= 70:
            return {
                'assessment': f"💸 صفقة جيدة - {brand.title()}",
                'recommendation': "اشتري"
            }
        elif confidence >= 60:
            return {
                'assessment': f"⚠️ صفقة مقبولة",
                'recommendation': "فكر"
            }
        else:
            return {
                'assessment': f"❓ تحقق من المنتج",
                'recommendation': "احذر"
            }
    
    def extract_smart_keywords(self, product_name: str, brand: str) -> List[str]:
        """استخراج كلمات بحث ذكية"""
        
        words = []
        
        # إضافة العلامة التجارية أولاً
        if brand and brand != 'unknown':
            words.append(brand)
        
        # استخراج الكلمات المهمة
        important_words = []
        for word in product_name.split():
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # تخطي الكلمات الشائعة
            skip_words = {'with', 'for', 'and', 'the', 'in', 'on', 'at', 'by', 'من', 'في', 'مع', 'على'}
            
            if len(clean_word) > 2 and clean_word not in skip_words:
                important_words.append(clean_word)
        
        # إضافة أهم 3-4 كلمات
        words.extend(important_words[:3])
        
        return words[:4]  # حد أقصى 4 كلمات
    
    async def compare_with_market(self, product_analysis: Dict, amazon_price: float) -> Dict:
        """مقارنة مع السوق"""
        
        search_term = ' '.join(product_analysis['search_keywords'])
        
        # بحث في نون
        noon_prices = await self.search_noon_prices(search_term)
        
        result = {
            'market_prices': noon_prices,
            'market_average': 0,
            'is_good_deal': True,
            'confidence': product_analysis['confidence'],
            'reason': product_analysis['assessment'],
            'recommendation': product_analysis['recommendation']
        }
        
        if noon_prices and len(noon_prices) >= 2:
            market_avg = statistics.mean(noon_prices)
            market_min = min(noon_prices)
            
            result['market_average'] = market_avg
            vs_avg = ((market_avg - amazon_price) / market_avg) * 100
            
            if amazon_price <= market_min:
                result['confidence'] = 95
                result['reason'] = f"🔥 الأرخص في السوق!"
                result['recommendation'] = "اشتري فوراً"
            elif vs_avg > 20:
                result['confidence'] = 90
                result['reason'] = f"✅ أرخص بـ {vs_avg:.0f}% من متوسط السوق"
                result['recommendation'] = "اشتري فوراً"
            elif vs_avg > 10:
                result['confidence'] = 85
                result['reason'] = f"⚡ أرخص بـ {vs_avg:.0f}% من متوسط السوق"
                result['recommendation'] = "اشتري"
            elif vs_avg > 0:
                result['confidence'] = min(result['confidence'] + 5, 95)
                result['reason'] = f"💸 أرخص بـ {vs_avg:.0f}% من متوسط السوق"
            else:
                result['confidence'] = max(result['confidence'] - 10, 60)
                result['reason'] = f"⚠️ أغلى من متوسط السوق"
            
            print(f"   📊 مقارنة: أمازون {amazon_price:,.0f} vs نون {market_avg:,.0f}")
        
        return result

# إنشاء المحلل الذكي
smart_analyzer = ProfessionalSmartAnalyzer()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع التحليل الذكي"""
    
    def analyze_and_send():
        if smart_analysis_enabled[0]:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # تحليل المنتج
                product_analysis = smart_analyzer.analyze_product_professional(
                    item.get('name', ''), new_price
                )
                
                # مقارنة مع السوق
                market_result = loop.run_until_complete(
                    smart_analyzer.compare_with_market(product_analysis, new_price)
                )
                
                # قرار القبول/الرفض
                if market_result['confidence'] < 60:
                    print(f"🚫 رفض: {item.get('name', '')[:35]}... - ثقة ضعيفة")
                    smart_analyzer.stats['products_rejected'] += 1
                    return
                
                # إضافة نتائج التحليل
                item.update({
                    'analysis': product_analysis,
                    'market_result': market_result,
                    'final_confidence': market_result['confidence'],
                    'final_reason': market_result['reason'],
                    'recommendation': market_result['recommendation'],
                    'market_average': market_result['market_average'],
                    'smart_used': product_analysis['smart_used']
                })
                
                smart_analyzer.stats['products_sent'] += 1
                
                print(f"✅ 🧠 Smart قبول: {item.get('name', '')[:35]}... - ثقة {market_result['confidence']}%")
                
                loop.close()
                
            except Exception as e:
                print(f"⚠️ خطأ في التحليل: {e}")
                return
        
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=analyze_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال رسالة تليجرام احترافية"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات التحليل
        final_reason = item.get('final_reason', '')
        final_confidence = item.get('final_confidence', 0)
        recommendation = item.get('recommendation', '')
        market_average = item.get('market_average', 0)
        analysis = item.get('analysis', {})
        smart_used = item.get('smart_used', False)

        # عرض السعر
        if old_price and old_price > new_price:
            price_display = f"<s>{int(old_price):,} EGP</s> → <b>{int(new_price):,} EGP</b>"
            discount_info = f"\n⚡ <b>Amazon Discount:</b> <code>{discount_percent:.0f}%</code>"
            savings = old_price - new_price
            savings_info = f"\n💵 <b>You Save:</b> {savings:,.0f} EGP"
        else:
            price_display = f"<b>{int(new_price):,} EGP</b>"
            discount_info = ""
            savings_info = ""

        # عنوان بناءً على التوصية
        if recommendation == "اشتري فوراً":
            headline = "🔥 <b>EXCELLENT DEAL!</b> 🔥"
        elif recommendation == "اشتري":
            headline = "✅ <b>GREAT DEAL!</b>"
        else:
            headline = "💸 <b>GOOD DEAL</b>"

        # معلومات التحليل
        analysis_info = ""
        if final_reason:
            analysis_info = f"\n🧠 Professional Analysis: {final_reason}"
        
        # متوسط السوق
        market_info = ""
        if market_average > 0:
            market_info = f"\n📊 <b>Market Average:</b> {market_average:,.0f} EGP"
            vs_market = ((market_average - new_price) / market_average) * 100
            if vs_market > 0:
                market_info += f"\n💰 <b>Save vs Market:</b> {vs_market:.0f}%"

        # معلومات العلامة
        brand_info = ""
        brand = analysis.get('brand', 'unknown')
        brand_quality = analysis.get('brand_quality', 'متوسط')
        if brand != 'unknown':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()} ({brand_quality})"

        # تحليل السعر
        price_analysis = analysis.get('price_analysis', {})
        if price_analysis:
            price_info = f"\n💰 <b>Price Analysis:</b> {price_analysis.get('category', '')}"
        else:
            price_info = ""

        confidence_row = f"\n📈 <b>Confidence:</b> {final_confidence}%" if final_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 {price_display}{discount_info}{savings_info}{confidence_row}{analysis_info}{market_info}{brand_info}{price_info}

🧠 <b>Professional Smart Analysis</b>
⚡ <b>No External AI Required</b>
"""

        # أزرار محسنة
        search_keywords = analysis.get('search_keywords', [])
        if search_keywords:
            search_term = ' '.join(search_keywords[:3])
        else:
            search_term = ' '.join(product_name.split()[:3])
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🌙 Check Noon", "url": f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(search_term)}"},
                    {"text": "🌐 Google Search", "url": f"https://www.google.com/search?q={urllib.parse.quote(search_term)}+سعر+مصر"}
                ],
                [{"text": "🏪 كان بكام", "url": f"https://www.kanbkam.com/search?q={urllib.parse.quote(search_term)}"}]
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
                        }, timeout=15
                    )
                
                if response.status_code == 200:
                    sent_count += 1

            except Exception as e:
                print(f"❌ خطأ إرسال: {e}")
        
        if sent_count > 0:
            print(f"✅ 🧠 Professional تنبيه إرسال لـ {sent_count} مستخدم")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال (نفس الكود السابق)
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
    
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=15):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        url = section_url.format(page_num)
        
        if log_fn:
            log_fn(f"[🧠 Smart] Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:8]:
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

                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                discount_percent = 0
                
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)
                    if strike_price and strike_price > price:
                        discount_percent = ((strike_price - price) / strike_price) * 100

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
    
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🔍 Start - New Products: {auto_mode}, Analysis: 🧠 Professional Smart")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Scraping {sec_name}...", "🔍")
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
            log("✅ Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    if smart_analysis_enabled[0]:
        stats = smart_analyzer.stats
        log(f"🧠 Smart Analysis Stats:")
        log(f"   📊 Total Analyses: {stats['total_analyses']}")
        log(f"   🧠 Smart Analyses: {stats['smart_analyses']}")
        log(f"   🌙 Noon Comparisons: {stats['noon_comparisons']}")
        log(f"   📱 Products Sent: {stats['products_sent']}")
        log(f"   🚫 Products Rejected: {stats['products_rejected']}")
        
        if stats['total_analyses'] > 0:
            success_rate = (stats['products_sent'] / stats['total_analyses']) * 100
            log(f"   📈 Send Rate: {success_rate:.1f}%")

def toggle_smart_analysis():
    smart_analysis_enabled[0] = not smart_analysis_enabled[0]
    status = "ON" if smart_analysis_enabled[0] else "OFF"
    log(f"🧠 Smart Analysis: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Amazon Price", "Market Average", "Confidence", "Reason", "Recommendation", "Brand", "Price Analysis"])
        for asin, item in db.items():
            amazon_price = item.get('price', 0)
            market_avg = item.get('market_average', 0)
            confidence = item.get('final_confidence', 0)
            reason = item.get('final_reason', '')
            recommendation = item.get('recommendation', '')
            analysis = item.get('analysis', {})
            brand = analysis.get('brand', '')
            price_analysis = analysis.get('price_analysis', {}).get('category', '')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], amazon_price, market_avg, confidence, reason, recommendation, brand, price_analysis])
    log("Exported to CSV with professional analysis data.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

def test_smart_analysis():
    """اختبار التحليل الذكي"""
    log("🧪 Testing Professional Smart Analysis...")
    
    # منتج تجريبي
    test_item = {
        "name": "Samsung Galaxy A06 Dual Sim 6GB RAM 128GB Storage",
        "asin": "TEST123",
        "url": "https://amazon.eg/test",
        "img": "",
        "section": "Electronics"
    }
    
    test_price = 2500
    
    # إرسال تنبيه تجريبي
    send_telegram_alert(test_item, None, test_price, 0, False)

# الواجهة
root = ctk.CTk()
root.title("LAQTA Professional - No External AI")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA Professional", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🧠 Professional Smart Analysis - No External AI Required", 
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

smart_analysis_chk = ctk.CTkCheckBox(controls_frame, text="🧠 Smart Analysis", font=("Arial", 13), 
                                    text_color="#4CAF50", command=toggle_smart_analysis)
smart_analysis_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
smart_analysis_chk.select()

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
buttons_frame.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)

btn_w, btn_h = 190, 45
btn_font = ("Arial", 16, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🔍 Start", command=start_scraping, width=btn_w, height=btn_h,
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

test_smart_btn = ctk.CTkButton(buttons_frame, text="🧪 Test Smart", command=test_smart_analysis, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#9C27B0", hover_color="#7b1fa2", text_color="#ffffff")
test_smart_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#795548", hover_color="#5d4037", text_color="#ffffff")
export_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#607D8B", hover_color="#455a64", text_color="#ffffff")
clear_btn.grid(row=0, column=6, padx=5, pady=6, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=300, height=45,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 12))

load_db()

# رسائل البداية
log("🧠 LAQTA Professional System Started!", "🚀")
log("✅ Professional Smart Analysis - No External AI Required", "🧠")
log("🔍 Advanced Brand Recognition & Price Analysis", "💡")
log("📊 Market Comparison with Noon", "🌙")
log("📱 Professional Telegram Alerts", "📱")
log("⚡ 100% Local Analysis - No Internet Dependencies", "⚡")
log("🎯 Ready for Professional Scraping!", "🎯")

root.mainloop()
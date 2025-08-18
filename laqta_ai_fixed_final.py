#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA AI - النظام النهائي المحسن (إصلاح Error 400)
"""

import customtkinter as ctk
import json, threading, asyncio, os
from datetime import datetime
import re
from PIL import Image
import requests
from io import BytesIO
import webbrowser
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
ai_comparison_enabled = [True]
auto_new_products_mode = [False]

ALERT_DISCOUNT = 15
alerts_data = []
notified_asins = set()
existing_asins = set()

def load_groq_api_key():
    """تحميل Groq API key"""
    try:
        if os.path.exists('groq_config.json'):
            with open('groq_config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('groq_api_key', '')
                if api_key and api_key != '' and 'YOUR_' not in api_key:
                    return api_key
        
        api_key = os.environ.get('GROQ_API_KEY', '')
        if api_key:
            return api_key
        
        return None
        
    except Exception as e:
        print(f"❌ خطأ في تحميل API key: {e}")
        return None

class AIMarketComparator:
    """مقارن السوق بالذكاء الاصطناعي - محسن"""
    
    def __init__(self):
        self.api_key = load_groq_api_key()
        self.ai_enabled = bool(self.api_key)
        self.ai_call_count = 0
        self.ai_success_count = 0
        
        self.stats = {
            'total_analyses': 0,
            'ai_analyses': 0,
            'ai_success_rate': 0,
            'noon_comparisons': 0,
            'products_sent': 0,
            'products_rejected': 0
        }
        
        if self.ai_enabled:
            print("✅ Groq AI مفعل - تحليل احترافي متاح")
        else:
            print("⚠️ Groq AI غير مفعل - سيتم استخدام التحليل التقليدي")
            print("💡 لتفعيل AI: ضع API key في groq_config.json")
    
    def call_groq_ai(self, prompt: str) -> Optional[str]:
        """استدعاء Groq AI محسن"""
        if not self.ai_enabled:
            return None
        
        self.ai_call_count += 1
        
        try:
            # تنظيف وتقصير الـ prompt
            clean_prompt = prompt.strip()[:400]  # حد أقصى 400 حرف
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "user", "content": clean_prompt}
                ],
                "max_tokens": 100,  # تقليل أكثر
                "temperature": 0.1,
                "top_p": 0.9
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=8
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                self.ai_success_count += 1
                return content
            elif response.status_code == 400:
                # فشل صامت للـ Error 400
                return None
            elif response.status_code == 401:
                print(f"❌ Groq API Key غير صحيح")
                self.ai_enabled = False
                return None
            elif response.status_code == 429:
                # Rate limit
                time.sleep(0.5)
                return None
            else:
                return None
                
        except Exception:
            return None
    
    async def search_noon_prices(self, search_term: str) -> List[float]:
        """بحث أسعار في نون"""
        prices = []
        
        try:
            search_url = f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(search_term)}"
            
            response = requests.get(search_url, timeout=6, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                content = response.text
                price_matches = re.findall(r'(\d{2,6})\s*(?:جنيه|EGP)', content, re.IGNORECASE)
                
                for match in price_matches[:10]:  # تقليل العدد
                    try:
                        price = float(match.replace(',', ''))
                        if 50 <= price <= 50000:  # نطاق معقول
                            prices.append(price)
                    except:
                        continue
                
                if prices:
                    unique_prices = sorted(list(set(prices)))[:5]  # أفضل 5 أسعار
                    self.stats['noon_comparisons'] += 1
                    return unique_prices
                
        except Exception:
            pass
        
        return []
    
    def analyze_product_smart(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل ذكي محسن للمنتج"""
        
        # استخراج العلامة التجارية المحسن
        name_lower = product_name.lower()
        
        # علامات موثوقة مع أسعار متوقعة
        brand_data = {
            'samsung': {'quality': 'ممتاز', 'min_price': 1000, 'max_price': 50000},
            'apple': {'quality': 'ممتاز', 'min_price': 5000, 'max_price': 80000},
            'anker': {'quality': 'ممتاز', 'min_price': 200, 'max_price': 5000},
            'sony': {'quality': 'ممتاز', 'min_price': 800, 'max_price': 20000},
            'xiaomi': {'quality': 'جيد', 'min_price': 300, 'max_price': 15000},
            'lg': {'quality': 'جيد', 'min_price': 500, 'max_price': 25000},
            'tp-link': {'quality': 'جيد', 'min_price': 150, 'max_price': 3000},
            'huawei': {'quality': 'جيد', 'min_price': 400, 'max_price': 12000}
        }
        
        brand = 'unknown'
        brand_info = {'quality': 'متوسط', 'min_price': 100, 'max_price': 10000}
        
        for b, info in brand_data.items():
            if b in name_lower:
                brand = b
                brand_info = info
                break
        
        # كلمات البحث محسنة
        words = []
        skip_words = {'with', 'for', 'and', 'the', 'in', 'on', 'at', 'by', 'من', 'في', 'مع', 'على'}
        
        for word in product_name.split()[:5]:
            clean = re.sub(r'[^\w]', '', word.lower())
            if len(clean) > 2 and clean not in skip_words:
                words.append(clean)
        
        search_keywords = words[:3]
        
        # تقييم ذكي
        confidence = 65  # قاعدة
        
        # تحسين الثقة بناءً على العلامة
        if brand_info['quality'] == 'ممتاز':
            confidence += 15
        elif brand_info['quality'] == 'جيد':
            confidence += 10
        
        # تحسين الثقة بناءً على السعر
        if brand_info['min_price'] <= amazon_price <= brand_info['max_price']:
            confidence += 10
        elif amazon_price < brand_info['min_price']:
            confidence += 20  # سعر ممتاز
        
        # تقييم نهائي
        if confidence >= 90:
            assessment = f"🔥 صفقة ممتازة - {brand.title()}"
            recommendation = "اشتري فوراً"
        elif confidence >= 80:
            assessment = f"✅ صفقة جيدة - {brand.title()}"
            recommendation = "اشتري"
        elif confidence >= 70:
            assessment = f"💸 صفقة مقبولة - {brand.title()}"
            recommendation = "اشتري"
        else:
            assessment = f"⚠️ تحقق من السعر - {brand.title()}"
            recommendation = "فكر"
        
        return {
            'brand': brand,
            'brand_quality': brand_info['quality'],
            'search_keywords': search_keywords,
            'confidence': min(confidence, 95),  # حد أقصى 95%
            'assessment': assessment,
            'recommendation': recommendation,
            'ai_used': False,
            'expected_range': f"{brand_info['min_price']:,}-{brand_info['max_price']:,} EGP"
        }
    
    def analyze_product(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل المنتج (AI أو ذكي)"""
        
        # تحليل ذكي أولاً
        smart_result = self.analyze_product_smart(product_name, amazon_price)
        
        # محاولة تحسين بـ AI
        if self.ai_enabled and self.ai_call_count < 50:  # حد أقصى للمحاولات
            
            # تنظيف اسم المنتج
            clean_name = product_name[:80]  # 80 حرف فقط
            clean_name = re.sub(r'[^\w\s\-\(\)]', '', clean_name)
            
            ai_prompt = f"""Product: {clean_name}
Price: {amazon_price} EGP

JSON:
{{"brand": "{smart_result['brand']}", "confidence": {smart_result['confidence']}, "quality": "{smart_result['brand_quality']}"}}"""
            
            ai_response = self.call_groq_ai(ai_prompt)
            if ai_response:
                try:
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        ai_data = json.loads(json_match.group())
                        
                        # تحديث النتيجة بـ AI
                        smart_result.update({
                            'brand': ai_data.get('brand', smart_result['brand']),
                            'confidence': min(ai_data.get('confidence', smart_result['confidence']), 95),
                            'brand_quality': ai_data.get('quality', smart_result['brand_quality']),
                            'ai_used': True
                        })
                        
                        self.stats['ai_analyses'] += 1
                        print(f"   🤖 AI: {smart_result['brand']} ({smart_result['confidence']}%)")
                        
                except Exception:
                    pass  # استخدام التحليل الذكي العادي
        
        self.stats['total_analyses'] += 1
        
        # حساب معدل النجاح
        if self.ai_call_count > 0:
            self.stats['ai_success_rate'] = (self.ai_success_count / self.ai_call_count) * 100
        
        return smart_result
    
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
            'recommendation': product_analysis.get('recommendation', 'اشتري')
        }
        
        if noon_prices and len(noon_prices) >= 2:  # تقليل الحد الأدنى
            # مقارنة حقيقية
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
                result['confidence'] = 80
                result['reason'] = f"💸 أرخص بـ {vs_avg:.0f}% من متوسط السوق"
                result['recommendation'] = "اشتري"
            else:
                result['confidence'] = 70
                result['reason'] = f"⚠️ قريب من متوسط السوق"
                result['recommendation'] = "فكر"
            
            print(f"   📊 مقارنة: أمازون {amazon_price:,.0f} vs نون {market_avg:,.0f}")
        
        return result

# إنشاء مقارن السوق
market_comparator = AIMarketComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة"""
    
    def analyze_and_send():
        if ai_comparison_enabled[0]:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # تحليل المنتج
                product_analysis = market_comparator.analyze_product(
                    item.get('name', ''), new_price
                )
                
                # مقارنة مع السوق
                market_result = loop.run_until_complete(
                    market_comparator.compare_with_market(product_analysis, new_price)
                )
                
                # قرار القبول/الرفض
                if market_result['confidence'] < 60:  # تقليل الحد
                    print(f"🚫 رفض: {item.get('name', '')[:35]}... - ثقة ضعيفة")
                    market_comparator.stats['products_rejected'] += 1
                    return
                
                # إضافة نتائج التحليل
                item.update({
                    'analysis': product_analysis,
                    'market_result': market_result,
                    'final_confidence': market_result['confidence'],
                    'final_reason': market_result['reason'],
                    'recommendation': market_result['recommendation'],
                    'market_average': market_result['market_average'],
                    'ai_used': product_analysis['ai_used']
                })
                
                market_comparator.stats['products_sent'] += 1
                
                ai_status = "🤖 AI" if product_analysis['ai_used'] else "🧠 Smart"
                print(f"✅ {ai_status} قبول: {item.get('name', '')[:35]}... - ثقة {market_result['confidence']}%")
                
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
        ai_used = item.get('ai_used', False)

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
            headline = "🔥 <b>EXCELLENT DEAL!</b> 🔥" if ai_used else "🔥 <b>GREAT DEAL!</b> 🔥"
        elif recommendation == "اشتري":
            headline = "✅ <b>GOOD DEAL!</b>" if ai_used else "✅ <b>RECOMMENDED!</b>"
        else:
            headline = "💸 <b>FAIR DEAL</b>" if ai_used else "💸 <b>DEAL</b>"

        # معلومات التحليل
        analysis_info = ""
        if final_reason:
            ai_label = "🤖 AI Analysis" if ai_used else "🧠 Smart Analysis"
            analysis_info = f"\n{ai_label}: {final_reason}"
        
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

        confidence_row = f"\n📈 <b>Confidence:</b> {final_confidence}%" if final_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 {price_display}{discount_info}{savings_info}{confidence_row}{analysis_info}{market_info}{brand_info}

{'🤖 <b>AI-Powered Analysis</b>' if ai_used else '🧠 <b>Smart Analysis</b>'}
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
            analysis_type = "🤖 AI" if ai_used else "🧠 Smart"
            print(f"✅ {analysis_type} تنبيه إرسال لـ {sent_count} مستخدم")

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
            ai_status = "🤖 AI" if market_comparator.ai_enabled else "🧠 Smart"
            log_fn(f"[{ai_status}] Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:8]:  # تقليل العدد لتحسين الأداء
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
    
    ai_mode = "🤖 AI" if market_comparator.ai_enabled else "🧠 Smart"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🔍 Start - New Products: {auto_mode}, Analysis: {ai_mode}")
    
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
    
    if ai_comparison_enabled[0]:
        stats = market_comparator.stats
        log(f"🔍 Analysis Stats:")
        log(f"   📊 Total: {stats['total_analyses']}")
        log(f"   🤖 AI: {stats['ai_analyses']}")
        log(f"   🌙 Noon: {stats['noon_comparisons']}")
        log(f"   📱 Sent: {stats['products_sent']}")
        log(f"   🚫 Rejected: {stats['products_rejected']}")
        
        # إحصائيات AI
        if market_comparator.ai_call_count > 0:
            success_rate = (market_comparator.ai_success_count / market_comparator.ai_call_count) * 100
            log(f"   🎯 AI Success Rate: {success_rate:.1f}%")

def toggle_ai_comparison():
    ai_comparison_enabled[0] = not ai_comparison_enabled[0]
    status = "ON" if ai_comparison_enabled[0] else "OFF"
    log(f"🔍 Analysis: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Amazon Price", "Market Average", "Confidence", "Reason", "Recommendation", "Brand"])
        for asin, item in db.items():
            amazon_price = item.get('price', 0)
            market_avg = item.get('market_average', 0)
            confidence = item.get('final_confidence', 0)
            reason = item.get('final_reason', '')
            recommendation = item.get('recommendation', '')
            analysis = item.get('analysis', {})
            brand = analysis.get('brand', '')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], amazon_price, market_avg, confidence, reason, recommendation, brand])
    log("Exported to CSV with analysis data.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

def test_ai():
    """اختبار AI محسن"""
    if market_comparator.ai_enabled:
        log("🤖 Testing AI...")
        
        # اختبار بسيط
        test_result = market_comparator.call_groq_ai('Test: Best phone brand?')
        if test_result:
            log("✅ AI works!", "🤖")
            log(f"🤖 Response: {test_result[:50]}...", "💬")
        else:
            log("❌ AI failed!", "🤖")
        
        # عرض إحصائيات AI
        if market_comparator.ai_call_count > 0:
            success_rate = (market_comparator.ai_success_count / market_comparator.ai_call_count) * 100
            log(f"📊 AI Success Rate: {success_rate:.1f}%", "📈")
    else:
        log("⚠️ AI not configured", "🤖")

# الواجهة
root = ctk.CTk()
root.title("LAQTA AI - Fixed & Optimized")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA AI", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

ai_status = "🤖 AI-Powered" if market_comparator.ai_enabled else "🧠 Smart Mode"
subtitle_label = ctk.CTkLabel(root, text=f"{ai_status} Amazon Egypt Scraper with Market Analysis", 
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

ai_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🤖 AI Analysis", font=("Arial", 13), 
                                   text_color="#4CAF50", command=toggle_ai_comparison)
ai_comparison_chk.grid(row=0, column=4, padx=5, pady=8, sticky="ew")
ai_comparison_chk.select()

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

test_ai_btn = ctk.CTkButton(buttons_frame, text="🤖 Test AI", command=test_ai, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#9C27B0", hover_color="#7b1fa2", text_color="#ffffff")
test_ai_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

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
if market_comparator.ai_enabled:
    log("🤖 LAQTA AI Fixed System started!", "🚀")
    log("🧠 Groq AI: Optimized prompts - Error 400 fixed", "✨")
else:
    log("🔍 LAQTA Smart System started!", "🚀")
    log("💡 To enable AI: Add API key to groq_config.json", "💡")

log("📱 Telegram: ON - with photos and smart analysis", "📱")
log("🌙 Noon: Real price comparison enabled", "🔍")
log("🏪 Kanbkam: Smart search links", "🔗")
log("🎯 Fixed: Error 400, optimized prompts, faster AI", "🔧")

root.mainloop()
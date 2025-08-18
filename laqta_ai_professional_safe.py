#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النظام الاحترافي بالذكاء الاصطناعي (النسخة الآمنة)
مقارنة ذكية بـ Groq AI + جميع الميزات المطلوبة
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

# إعداد الواجهة الأصلية
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

ALERT_DISCOUNT = 10
alerts_data = []
notified_asins = set()
existing_asins = set()

# إعداد Groq AI - ضع API key هنا
def load_groq_api_key():
    """تحميل Groq API key من ملف الإعدادات أو المتغير"""
    try:
        # محاولة قراءة من ملف الإعدادات
        if os.path.exists('groq_config.json'):
            with open('groq_config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('groq_api_key', '')
                if api_key and api_key != 'YOUR_GROQ_API_KEY_HERE':
                    return api_key
        
        # محاولة قراءة من متغير البيئة
        api_key = os.environ.get('GROQ_API_KEY', '')
        if api_key:
            return api_key
        
        # إذا لم نجد API key
        print("⚠️ لم يتم العثور على Groq API key")
        print("💡 ضع API key في groq_config.json أو متغير البيئة GROQ_API_KEY")
        return None
        
    except Exception as e:
        print(f"❌ خطأ في تحميل API key: {e}")
        return None

class GroqAIProfessionalComparator:
    """مقارن احترافي بالذكاء الاصطناعي"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or load_groq_api_key()
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-70b-versatile"
        
        self.stats = {
            'total_ai_analyses': 0,
            'successful_ai_analyses': 0,
            'ai_comparisons': 0,
            'products_sent': 0,
            'products_rejected': 0,
            'noon_searches': 0,
            'noon_successes': 0,
            'avg_ai_time': 0,
            'tokens_used': 0
        }
        
        self.ai_cache = {}
        self.last_ai_call = 0
        self.min_ai_delay = 1.0
        
        # فحص API key
        if not self.api_key or self.api_key == 'YOUR_GROQ_API_KEY_HERE':
            print("⚠️ Groq AI غير مفعل - API key مفقود")
            print("💡 اقرأ SETUP_API_KEY.md لمعرفة كيفية الحصول على API key مجاني")
            self.ai_enabled = False
        else:
            print("✅ Groq AI مفعل - جاهز للتحليل الذكي")
            self.ai_enabled = True
    
    def call_groq_ai(self, prompt: str, max_tokens: int = 400) -> Optional[str]:
        """استدعاء Groq AI مع معالجة الأخطاء"""
        
        if not self.ai_enabled:
            return None
        
        # تحكم في السرعة
        current_time = time.time()
        if current_time - self.last_ai_call < self.min_ai_delay:
            time.sleep(self.min_ai_delay - (current_time - self.last_ai_call))
        self.last_ai_call = time.time()
        
        try:
            start_time = time.time()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "أنت خبير محترف في تحليل المنتجات والأسعار في السوق المصري. تقدم تحليلات دقيقة ومفيدة بصيغة JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
                "top_p": 0.9
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=20
            )
            
            ai_time = time.time() - start_time
            self.stats['avg_ai_time'] = (
                (self.stats['avg_ai_time'] * self.stats['total_ai_analyses'] + ai_time) / 
                (self.stats['total_ai_analyses'] + 1)
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                if 'usage' in result:
                    self.stats['tokens_used'] += result['usage'].get('total_tokens', 0)
                
                self.stats['successful_ai_analyses'] += 1
                return content.strip()
            else:
                print(f"❌ Groq AI Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Groq AI Exception: {e}")
            return None
        finally:
            self.stats['total_ai_analyses'] += 1
    
    async def search_noon_with_ai_keywords(self, ai_keywords: List[str]) -> List[float]:
        """بحث في نون باستخدام كلمات AI المحسنة"""
        
        prices = []
        
        # جرب كل كلمة مفتاحية من AI
        for keyword_set in [ai_keywords[:2], ai_keywords[:3], ai_keywords]:
            if prices:
                break
                
            search_term = ' '.join(keyword_set)
            
            try:
                search_url = f"https://www.noon.com/egypt-en/search/?q={urllib.parse.quote(search_term)}"
                
                response = requests.get(search_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    content = response.text
                    
                    # البحث عن الأسعار
                    price_patterns = [
                        r'(\d{2,6})\s*(?:جنيه|EGP)',
                        r'"price":\s*(\d+)',
                        r'data-price="(\d+)"'
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches[:20]:
                            try:
                                price = float(match.replace(',', ''))
                                if 50 <= price <= 200000:
                                    prices.append(price)
                            except:
                                continue
                        
                        if len(prices) >= 5:
                            break
                    
                    if prices:
                        print(f"      🌙 نون: وجدت {len(prices)} أسعار بكلمات '{search_term}'")
                        self.stats['noon_successes'] += 1
                        break
                
            except Exception as e:
                print(f"      ⚠️ نون خطأ مع '{search_term}': {e}")
                continue
        
        self.stats['noon_searches'] += 1
        
        # تنظيف وفلترة الأسعار
        if prices:
            unique_prices = sorted(list(set(prices)))
            
            if len(unique_prices) > 6:
                median = statistics.median(unique_prices)
                filtered = []
                for price in unique_prices:
                    if 0.2 * median <= price <= 5 * median:
                        filtered.append(price)
                
                if len(filtered) >= 3:
                    unique_prices = filtered
            
            return unique_prices[:10]
        
        return []
    
    async def ai_professional_analysis(self, product_name: str, amazon_price: float) -> Dict:
        """تحليل احترافي كامل بالذكاء الاصطناعي"""
        
        cache_key = f"ai_pro_{product_name[:25]}_{amazon_price}"
        
        if cache_key in self.ai_cache:
            return self.ai_cache[cache_key]
        
        print(f"🤖 AI تحليل احترافي: {product_name[:40]}...")
        
        # إذا AI غير مفعل، استخدم التحليل الاحتياطي
        if not self.ai_enabled:
            return self.create_fallback_result(product_name, amazon_price, "AI غير مفعل")
        
        # تحليل المنتج بـ AI
        product_analysis_prompt = f"""
تحليل احترافي لمنتج من أمازون مصر:

المنتج: {product_name}
السعر: {amazon_price} EGP

المطلوب تحليل شامل ودقيق:
1. العلامة التجارية الحقيقية (تجاهل "compatible with" أو "for")
2. نوع المنتج بدقة
3. أفضل 3 كلمات للبحث في المواقع المصرية
4. النطاق السعري المتوقع في مصر
5. تقييم جودة العلامة التجارية
6. منطقية السعر (1-10)
7. هل يستحق المقارنة؟

JSON فقط:
{{
    "brand": "العلامة الحقيقية",
    "brand_quality": "ممتاز/جيد/متوسط/ضعيف",
    "product_type": "نوع المنتج",
    "search_keywords": ["كلمة1", "كلمة2", "كلمة3"],
    "expected_min": 0,
    "expected_max": 0,
    "price_logic": 1-10,
    "worth_comparing": true/false,
    "assessment": "تقييم مختصر",
    "confidence": 0-100
}}
"""
        
        ai_product_response = self.call_groq_ai(product_analysis_prompt, 350)
        
        if not ai_product_response:
            return self.create_fallback_result(product_name, amazon_price, "AI فشل في تحليل المنتج")
        
        try:
            # استخراج JSON من رد AI
            json_match = re.search(r'\{.*\}', ai_product_response, re.DOTALL)
            if not json_match:
                return self.create_fallback_result(product_name, amazon_price, "AI لم يرد بـ JSON صحيح")
            
            ai_product_data = json.loads(json_match.group())
            
            print(f"   🤖 AI تحليل: {ai_product_data.get('brand', 'unknown')} ({ai_product_data.get('brand_quality', 'متوسط')})")
            print(f"   🔍 AI كلمات: {ai_product_data.get('search_keywords', [])}")
            
            # البحث في نون بكلمات AI
            search_keywords = ai_product_data.get('search_keywords', [])
            if search_keywords:
                competitor_prices = await self.search_noon_with_ai_keywords(search_keywords)
            else:
                competitor_prices = []
            
            # مقارنة ذكية بـ AI (إذا وجدت أسعار)
            if competitor_prices and len(competitor_prices) >= 3:
                comparison_result = await self.ai_smart_comparison(
                    product_name, amazon_price, competitor_prices, ai_product_data
                )
                self.stats['ai_comparisons'] += 1
            else:
                comparison_result = self.ai_no_comparison_assessment(ai_product_data, amazon_price)
            
            # دمج النتائج
            final_result = {
                **ai_product_data,
                **comparison_result,
                'ai_analysis_success': True,
                'competitor_prices': competitor_prices
            }
            
            # حفظ في الكاش
            self.ai_cache[cache_key] = final_result
            
            return final_result
            
        except json.JSONDecodeError as e:
            print(f"   ❌ AI JSON خطأ: {e}")
            return self.create_fallback_result(product_name, amazon_price, "AI JSON خطأ")
        except Exception as e:
            print(f"   ❌ AI خطأ عام: {e}")
            return self.create_fallback_result(product_name, amazon_price, f"AI خطأ: {e}")
    
    async def ai_smart_comparison(self, product_name: str, amazon_price: float, competitor_prices: List[float], product_data: Dict) -> Dict:
        """مقارنة ذكية بـ AI"""
        
        market_stats = {
            'average': statistics.mean(competitor_prices),
            'min': min(competitor_prices),
            'max': max(competitor_prices),
            'count': len(competitor_prices)
        }
        
        comparison_prompt = f"""
مقارنة احترافية للأسعار في السوق المصري:

المنتج: {product_name}
العلامة: {product_data.get('brand', 'unknown')} ({product_data.get('brand_quality', 'متوسط')})
النوع: {product_data.get('product_type', 'منتج')}

سعر أمازون: {amazon_price} EGP

إحصائيات السوق:
- عدد الأسعار: {market_stats['count']}
- متوسط السوق: {market_stats['average']:.0f} EGP
- أقل سعر: {market_stats['min']:.0f} EGP
- أعلى سعر: {market_stats['max']:.0f} EGP

المطلوب تحليل احترافي:
1. هل سعر أمازون جيد مقارنة بالسوق؟
2. ما ترتيبه بين المنافسين؟
3. نسبة الوفر/الزيادة؟
4. مستوى الصفقة؟
5. التوصية النهائية؟
6. مستوى الثقة؟

JSON فقط:
{{
    "is_excellent_deal": true/false,
    "market_position": "الأرخص/ثاني أرخص/متوسط/غالي",
    "vs_average_percent": 0,
    "deal_quality": "ممتاز/جيد/متوسط/ضعيف",
    "confidence": 0-100,
    "reason": "سبب مفصل",
    "recommendation": "اشتري فوراً/اشتري/فكر/تجاهل"
}}
"""
        
        print(f"   🤖 AI مقارنة: {amazon_price:,.0f} vs متوسط {market_stats['average']:,.0f}")
        
        ai_response = self.call_groq_ai(comparison_prompt, 300)
        
        if ai_response:
            try:
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    ai_comparison = json.loads(json_match.group())
                    
                    result = {
                        'market_average': market_stats['average'],
                        'market_min': market_stats['min'],
                        'market_max': market_stats['max'],
                        'competitor_count': market_stats['count'],
                        'is_good_deal': ai_comparison.get('is_excellent_deal', True),
                        'market_position': ai_comparison.get('market_position', 'متوسط'),
                        'vs_average_percent': float(ai_comparison.get('vs_average_percent', 0)),
                        'deal_quality': ai_comparison.get('deal_quality', 'جيد'),
                        'confidence': int(ai_comparison.get('confidence', 75)),
                        'detailed_reason': ai_comparison.get('reason', 'تحليل AI'),
                        'recommendation': ai_comparison.get('recommendation', 'اشتري'),
                        'comparison_type': 'ai_market_comparison'
                    }
                    
                    print(f"   🤖 AI نتيجة: {result['deal_quality']} - {result['recommendation']} - ثقة {result['confidence']}%")
                    
                    return result
                
            except Exception as e:
                print(f"   ❌ AI مقارنة خطأ: {e}")
        
        # فشل AI - حساب تقليدي
        return self.traditional_comparison(amazon_price, market_stats)
    
    def ai_no_comparison_assessment(self, product_data: Dict, amazon_price: float) -> Dict:
        """تقييم AI عند عدم وجود مقارنة"""
        
        brand_quality = product_data.get('brand_quality', 'متوسط')
        price_logic = product_data.get('price_logic', 5)
        
        if brand_quality == 'ممتاز' and price_logic >= 8:
            confidence = 85
            reason = f"علامة ممتازة + سعر منطقي - صفقة ممتازة"
            recommendation = "اشتري فوراً"
        elif brand_quality == 'ممتاز':
            confidence = 80
            reason = f"علامة ممتازة - صفقة جيدة"
            recommendation = "اشتري"
        elif brand_quality == 'جيد' and price_logic >= 7:
            confidence = 75
            reason = f"علامة جيدة + سعر منطقي"
            recommendation = "اشتري"
        elif brand_quality == 'جيد':
            confidence = 70
            reason = f"علامة جيدة"
            recommendation = "اشتري"
        else:
            confidence = 65
            reason = f"منتج مقبول"
            recommendation = "فكر"
        
        return {
            'market_average': 0,
            'is_good_deal': True,
            'confidence': confidence,
            'detailed_reason': reason,
            'recommendation': recommendation,
            'comparison_type': 'ai_no_comparison',
            'deal_quality': brand_quality
        }
    
    def traditional_comparison(self, amazon_price: float, market_stats: Dict) -> Dict:
        """مقارنة تقليدية عند فشل AI"""
        
        vs_average = ((market_stats['average'] - amazon_price) / market_stats['average']) * 100
        
        if amazon_price <= market_stats['min']:
            confidence = 90
            reason = "الأرخص في السوق"
            recommendation = "اشتري فوراً"
        elif vs_average > 15:
            confidence = 85
            reason = f"أرخص بـ {vs_average:.0f}% من المتوسط"
            recommendation = "اشتري"
        elif vs_average > 0:
            confidence = 75
            reason = f"أرخص بـ {vs_average:.0f}% من المتوسط"
            recommendation = "اشتري"
        else:
            confidence = 65
            reason = f"قريب من متوسط السوق"
            recommendation = "فكر"
        
        return {
            'market_average': market_stats['average'],
            'market_min': market_stats['min'],
            'market_max': market_stats['max'],
            'competitor_count': market_stats['count'],
            'is_good_deal': vs_average > -15,
            'vs_average_percent': vs_average,
            'confidence': confidence,
            'detailed_reason': reason,
            'recommendation': recommendation,
            'comparison_type': 'traditional_comparison'
        }
    
    def create_fallback_result(self, product_name: str, amazon_price: float, error_msg: str) -> Dict:
        """نتيجة احتياطية عند فشل AI"""
        
        name_lower = product_name.lower()
        trusted_brands = ['samsung', 'apple', 'xiaomi', 'anker', 'sony', 'lg']
        
        brand = 'unknown'
        for b in trusted_brands:
            if b in name_lower:
                brand = b
                break
        
        if brand in ['samsung', 'apple', 'anker']:
            confidence = 75
            reason = f"علامة ممتازة ({brand}) - قبول احتياطي"
        elif brand != 'unknown':
            confidence = 70
            reason = f"علامة معروفة ({brand}) - قبول احتياطي"
        else:
            confidence = 65
            reason = "منتج مقبول - تحليل احتياطي"
        
        return {
            'brand': brand,
            'brand_quality': 'جيد' if brand != 'unknown' else 'متوسط',
            'confidence': confidence,
            'detailed_reason': reason,
            'recommendation': 'اشتري',
            'comparison_type': 'fallback',
            'ai_analysis_success': False,
            'error_message': error_msg,
            'is_good_deal': True,
            'market_average': 0
        }
    
    def get_ai_stats(self) -> Dict:
        """إحصائيات AI"""
        total = max(self.stats['total_ai_analyses'], 1)
        return {
            'total_ai_analyses': self.stats['total_ai_analyses'],
            'successful_ai_analyses': self.stats['successful_ai_analyses'],
            'success_rate': (self.stats['successful_ai_analyses'] / total) * 100,
            'avg_response_time': self.stats['avg_ai_time'],
            'tokens_used': self.stats['tokens_used'],
            'cache_size': len(self.ai_cache)
        }

# إنشاء محلل AI الاحترافي
ai_comparator = GroqAIProfessionalComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع التحليل الذكي الاحترافي"""
    
    def ai_analyze_and_send():
        """تحليل AI ومقارنة وإرسال"""
        
        if ai_comparison_enabled[0]:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                ai_result = loop.run_until_complete(
                    ai_comparator.ai_professional_analysis(
                        item.get('name', ''), new_price
                    )
                )
                
                # قرار بناءً على تحليل AI
                if not ai_result.get('is_good_deal', True) or ai_result.get('confidence', 0) < 60:
                    print(f"🤖 AI رفض: {item.get('name', '')[:35]}... - {ai_result.get('detailed_reason', 'ضعيف')}")
                    ai_comparator.stats['products_rejected'] += 1
                    return
                
                # إضافة نتائج AI للمنتج
                item['ai_analysis'] = ai_result
                item['ai_confidence'] = ai_result.get('confidence', 70)
                item['ai_reason'] = ai_result.get('detailed_reason', 'تحليل AI')
                item['ai_recommendation'] = ai_result.get('recommendation', 'اشتري')
                item['market_average'] = ai_result.get('market_average', 0)
                item['brand'] = ai_result.get('brand', 'unknown')
                item['brand_quality'] = ai_result.get('brand_quality', 'متوسط')
                item['comparison_type'] = ai_result.get('comparison_type', 'ai_analysis')
                
                ai_comparator.stats['products_sent'] += 1
                
                print(f"🤖 AI قبول: {item.get('name', '')[:35]}... - ثقة {ai_result.get('confidence', 70)}%")
                
                loop.close()
                
            except Exception as e:
                print(f"⚠️ AI خطأ عام: {e}")
                # قبول احتياطي للمنتجات مع خصم جيد
                if discount_percent >= 20:
                    item['ai_confidence'] = 65
                    item['ai_reason'] = f"خصم جيد {discount_percent:.0f}% - قبول احتياطي"
                    item['comparison_type'] = 'error_fallback'
                    ai_comparator.stats['products_sent'] += 1
                else:
                    return
        
        # إرسال الرسالة مع الصورة
        send_ai_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=ai_analyze_and_send, daemon=True).start()

def send_ai_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع تحليل AI احترافي"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات تحليل AI
        ai_reason = item.get('ai_reason', '')
        ai_confidence = item.get('ai_confidence', 0)
        ai_recommendation = item.get('ai_recommendation', '')
        market_average = item.get('market_average', 0)
        brand = item.get('brand', 'unknown')
        brand_quality = item.get('brand_quality', 'متوسط')
        comparison_type = item.get('comparison_type', 'unknown')

        # عرض السعر مع الخصم
        if old_price and old_price > new_price:
            price_display = f"<s>{int(old_price):,} EGP</s> → <b>{int(new_price):,} EGP</b>"
            discount_info = f"\n⚡ <b>Amazon Discount:</b> <code>{discount_percent:.0f}%</code>"
            savings = old_price - new_price
            savings_info = f"\n💵 <b>Amazon Savings:</b> {savings:,.0f} EGP"
        else:
            price_display = f"<b>{int(new_price):,} EGP</b>"
            discount_info = ""
            savings_info = ""

        # عنوان بناءً على توصية AI
        if ai_recommendation == "اشتري فوراً":
            headline = "🤖 <b>AI RECOMMENDS: BUY NOW!</b> 🔥"
        elif ai_recommendation == "اشتري":
            headline = "🤖 <b>AI RECOMMENDS: BUY!</b> ✅"
        elif ai_recommendation == "فكر":
            headline = "🤖 <b>AI SAYS: CONSIDER</b> ⚡"
        else:
            headline = "🤖 <b>AI ANALYSIS</b> 💸"

        # معلومات AI
        ai_info = ""
        if ai_reason:
            ai_info = f"\n🤖 <b>AI Analysis:</b> {ai_reason}"
        
        # متوسط السوق
        market_info = ""
        if market_average > 0:
            market_info = f"\n📊 <b>Market Average:</b> {market_average:,.0f} EGP"
            vs_market = ((market_average - new_price) / market_average) * 100
            if vs_market > 0:
                market_info += f"\n💰 <b>Save vs Market:</b> {vs_market:.0f}%"
            else:
                market_info += f"\n⚠️ <b>Above Market:</b> {abs(vs_market):.0f}%"
        
        # معلومات العلامة التجارية
        brand_info = ""
        if brand and brand != 'unknown':
            brand_info = f"\n🏷️ <b>Brand:</b> {brand.title()} ({brand_quality})"
        
        # معلومات نوع التحليل
        method_info = ""
        if comparison_type == 'ai_market_comparison':
            method_info = f"\n📊 <b>Method:</b> AI Market Comparison"
        elif comparison_type == 'ai_no_comparison':
            method_info = f"\n📊 <b>Method:</b> AI Brand Analysis"
        elif comparison_type == 'fallback':
            method_info = f"\n📊 <b>Method:</b> Backup Analysis"
        
        confidence_row = f"\n📈 <b>AI Confidence:</b> {ai_confidence}%" if ai_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 {price_display}{discount_info}{savings_info}{confidence_row}{ai_info}{market_info}{brand_info}{method_info}

🤖 <b>AI-Powered Professional Analysis</b>
"""

        # أزرار محسنة مع كلمات AI
        ai_analysis = item.get('ai_analysis', {})
        search_keywords = ai_analysis.get('search_keywords', [])
        
        if search_keywords:
            search_term = ' '.join(search_keywords[:3])
        else:
            words = product_name.split()[:3]
            search_term = ' '.join(word.lower() for word in words)
        
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
            method_text = "AI مقارنة" if comparison_type == 'ai_market_comparison' else "AI تحليل"
            print(f"🤖 تم إرسال AI تنبيه لـ {sent_count} مستخدم - ثقة {ai_confidence}% ({method_text})")

    except Exception as e:
        print("❌ Telegram AI Error:", e)

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
    """إضافة بيانات التنبيه مع تحليل AI"""
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
    
    # إرسال مع تحليل AI
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة مع AI
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=10):
    """سكرابة صفحة واحدة مع تحليل AI"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[AI PROFESSIONAL]" if ai_comparison_enabled[0] else ""
            log_fn(f"🤖 {mode} Scraping: {section}, page {page_num}")
        
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

                # إرسال للتحليل AI
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
            log_fn(f"[Page {page_num}] 🤖 {new_count} NEW products")
        
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
    
    ai_mode = "AI PROFESSIONAL ON" if ai_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🤖 AI Professional Start - New Products: {auto_mode}, AI: {ai_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"AI professional scraping {sec_name}...", "🤖")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🤖"),
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
                            log_fn=lambda m: log(m, "🤖"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ AI Scraper error: {e}")
        finally:
            save_db()
            log("🤖 AI Professional Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 AI Professional Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    if ai_comparison_enabled[0]:
        ai_stats = ai_comparator.get_ai_stats()
        log(f"🤖 AI Professional Stats:")
        log(f"   📊 Total AI Analyses: {ai_stats['total_ai_analyses']}")
        log(f"   ✅ Successful AI Analyses: {ai_stats['successful_ai_analyses']}")
        log(f"   📊 AI Comparisons: {ai_comparator.stats['ai_comparisons']}")
        log(f"   📱 Products Sent: {ai_comparator.stats['products_sent']}")
        log(f"   🚫 Products Rejected: {ai_comparator.stats['products_rejected']}")
        log(f"   🌙 Noon Searches: {ai_comparator.stats['noon_searches']}")
        log(f"   ✅ Noon Successes: {ai_comparator.stats['noon_successes']}")
        log(f"   📈 AI Success Rate: {ai_stats['success_rate']:.1f}%")
        log(f"   ⏱️ Avg AI Time: {ai_stats['avg_response_time']:.1f}s")
        log(f"   🎯 Tokens Used: {ai_stats['tokens_used']}")
        log(f"   🧠 Cache Size: {ai_stats['cache_size']}")

def toggle_ai_comparison():
    ai_comparison_enabled[0] = not ai_comparison_enabled[0]
    status = "AI PROFESSIONAL ON" if ai_comparison_enabled[0] else "OFF"
    log(f"🤖 AI Professional: {status}")

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
    with open("products_export_ai.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Amazon Price", "Market Average", "AI Confidence", "AI Reason", "AI Recommendation", "Brand", "Brand Quality"])
        for asin, item in db.items():
            amazon_price = item.get('price', 0)
            market_avg = item.get('market_average', 0)
            ai_confidence = item.get('ai_confidence', 0)
            ai_reason = item.get('ai_reason', '')
            ai_recommendation = item.get('ai_recommendation', '')
            brand = item.get('brand', '')
            brand_quality = item.get('brand_quality', '')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], amazon_price, market_avg, ai_confidence, ai_reason, ai_recommendation, brand, brand_quality])
    log("Exported to CSV with AI professional analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

def test_ai_connection():
    """اختبار اتصال AI"""
    log("🤖 Testing AI connection...")
    
    if not ai_comparator.ai_enabled:
        log("❌ AI not configured - check SETUP_API_KEY.md", "🤖")
        return
    
    test_result = ai_comparator.call_groq_ai("اختبار سريع: ما هو أفضل موقع للتسوق في مصر؟", 50)
    
    if test_result:
        log("✅ AI connection successful!", "🤖")
        log(f"AI response preview: {test_result[:100]}...")
    else:
        log("❌ AI connection failed!", "🤖")

# الواجهة الاحترافية
root = ctk.CTk()
root.title("LAQTA - AI Professional Analysis")
root.geometry("1600x1000")
root.minsize(1400, 800)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA AI", font=("SST Arabic Medium", 60), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="🤖 AI-Powered Professional Amazon Egypt Scraper with Smart Market Analysis", 
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

ai_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🤖 AI Pro", font=("Arial", 13), 
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

progress_bar = ctk.CTkProgressBar(root, height=30, progress_color="#59ff9d", fg_color="#232d3a")
progress_bar.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
progress_bar.set(0.0)

log_textbox = ctk.CTkTextbox(root, font=("Consolas", 13), fg_color="#20242f", text_color="#c2ffe3", border_width=0, height=280)
log_textbox.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
log_textbox.configure(state="disabled")

buttons_frame = ctk.CTkFrame(root, fg_color="transparent")
buttons_frame.grid(row=5, column=0, padx=10, pady=8, sticky="ew")
buttons_frame.grid_columnconfigure((0,1,2,3,4,5,6), weight=1)

btn_w, btn_h = 180, 50
btn_font = ("Arial", 15, "bold")

start_btn = ctk.CTkButton(buttons_frame, text="🤖 AI Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 AI Stats", command=show_stats, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#FF9800", hover_color="#e68900", text_color="#ffffff")
stats_btn.grid(row=0, column=3, padx=5, pady=6, sticky="ew")

test_ai_btn = ctk.CTkButton(buttons_frame, text="🤖 Test AI", command=test_ai_connection, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#9C27B0", hover_color="#7b1fa2", text_color="#ffffff")
test_ai_btn.grid(row=0, column=4, padx=5, pady=6, sticky="ew")

export_btn = ctk.CTkButton(buttons_frame, text="📁 Export", command=export_csv, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#795548", hover_color="#5d4037", text_color="#ffffff")
export_btn.grid(row=0, column=5, padx=5, pady=6, sticky="ew")

clear_btn = ctk.CTkButton(buttons_frame, text="🧹 Clear", command=clear_log, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#607D8B", hover_color="#455a64", text_color="#ffffff")
clear_btn.grid(row=0, column=6, padx=5, pady=6, sticky="ew")

exit_btn = ctk.CTkButton(root, text="Exit ❌", command=exit_app, width=350, height=50,
    font=("Arial Black", 18), fg_color="#232d3a", hover_color="#fa1a50", text_color="#59ff9d")
exit_btn.grid(row=6, column=0, pady=(8, 12))

load_db()

# رسائل البداية
if ai_comparator.ai_enabled:
    log("🤖 LAQTA AI Professional Analysis System started!", "🚀")
    log("🧠 Groq AI: Llama 3.1 70B for professional product analysis", "✨")
    log("🔍 Smart Search: AI-generated keywords for Egyptian market", "💡")
    log("📊 AI Comparison: Intelligent price analysis and market positioning", "📈")
else:
    log("🤖 LAQTA AI Professional System started (AI disabled)", "🚀")
    log("⚠️ Groq AI: Not configured - using fallback analysis", "⚠️")
    log("💡 To enable AI: Add API key to groq_config.json", "💡")

log("📸 Telegram: ON - with photos and professional analysis", "📱")
log("⚡ Speed: Smart caching, optimized performance", "🏃")
log("🎯 Strategy: AI analyzes → AI searches → AI compares → Professional results", "🤖")
log("📱 Expected: PROFESSIONAL AI-powered market analysis!", "🏆")

root.mainloop()
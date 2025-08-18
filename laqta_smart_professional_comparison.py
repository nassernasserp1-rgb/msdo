#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - النظام الذكي والاحترافي للمقارنة
مقارنة ذكية بناءً على تحليل وصف المنتج + روابط محسنة
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

ALERT_DISCOUNT = 25
alerts_data = []
notified_asins = set()
existing_asins = set()

class SmartProductAnalyzer:
    """محلل ذكي لوصف المنتج واستخراج المعلومات المهمة"""
    
    def __init__(self):
        self.product_patterns = {
            # أنماط الهواتف
            'phone': {
                'patterns': [r'(\w+)\s+(\w+\s*\w*)\s+(\d+gb|\d+\s*gb)', r'(\w+)\s+(galaxy|iphone|redmi|note)\s*(\d+)', 
                           r'(\w+)\s+(\w+)\s+(smartphone|phone|mobile)'],
                'important_specs': ['gb', 'ram', 'storage', '5g', '4g', 'dual sim', 'camera', 'mp'],
                'category': 'smartphones'
            },
            # أنماط الشواحن
            'charger': {
                'patterns': [r'(\w+)\s+(charger|شاحن)\s*(\d+w|\d+\s*w)', r'(\w+)\s+(usb|type-c|lightning)\s+(charger|cable)'],
                'important_specs': ['w', 'watt', 'usb-c', 'type-c', 'lightning', 'fast', 'quick', 'pd'],
                'category': 'chargers'
            },
            # أنماط الشاشات
            'monitor': {
                'patterns': [r'(\w+)\s+(\d+)-?inch\s+(monitor|screen|display)', r'(\w+)\s+(\d+)\s*(inch|")\s+(curved|gaming|4k)'],
                'important_specs': ['inch', 'fhd', '4k', 'qhd', 'curved', 'gaming', 'hz', 'ips'],
                'category': 'monitors'
            },
            # أنماط التلفزيونات
            'tv': {
                'patterns': [r'(\w+)\s+(\d+)-?inch\s+(tv|television|smart tv)', r'(\w+)\s+(\d+)\s*(inch|")\s+(fhd|4k|smart)'],
                'important_specs': ['inch', 'smart', '4k', 'fhd', 'led', 'android', 'webos'],
                'category': 'televisions'
            },
            # أنماط منتجات العناية
            'beauty': {
                'patterns': [r'(\w+)\s+(cream|lotion|shampoo|perfume)', r'(\w+)\s+(\w+)\s+(ml|gm|oz)'],
                'important_specs': ['ml', 'gm', 'oz', 'anti-aging', 'moisturizing', 'organic'],
                'category': 'beauty'
            }
        }
    
    def analyze_product_description(self, product_name: str) -> dict:
        """تحليل ذكي لوصف المنتج واستخراج المعلومات المهمة"""
        
        name_lower = product_name.lower()
        analysis = {
            'brand': 'unknown',
            'model': 'unknown',
            'category': 'general',
            'key_specs': [],
            'search_terms': [],
            'confidence': 0
        }
        
        # استخراج العلامة التجارية (أول كلمة عادة)
        words = product_name.split()
        if words:
            potential_brand = words[0].lower()
            known_brands = ['samsung', 'xiaomi', 'apple', 'sony', 'lg', 'anker', 'tp-link', 'wd', 'haier']
            if potential_brand in known_brands:
                analysis['brand'] = potential_brand
                analysis['confidence'] += 20
        
        # تحليل نوع المنتج
        for product_type, config in self.product_patterns.items():
            for pattern in config['patterns']:
                match = re.search(pattern, name_lower)
                if match:
                    analysis['category'] = config['category']
                    analysis['confidence'] += 30
                    
                    # استخراج المواصفات المهمة
                    for spec in config['important_specs']:
                        if spec in name_lower:
                            analysis['key_specs'].append(spec)
                            analysis['confidence'] += 5
                    break
        
        # بناء مصطلحات البحث الذكية
        search_terms = []
        
        # إضافة العلامة التجارية إذا معروفة
        if analysis['brand'] != 'unknown':
            search_terms.append(analysis['brand'])
        
        # إضافة كلمات مهمة من الوصف
        important_words = []
        for word in words[:6]:  # أول 6 كلمات
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if (len(clean_word) > 2 and 
                clean_word not in ['new', 'original', 'pack', 'set', 'amazon', 'choice', 'with', 'for']):
                important_words.append(clean_word)
        
        # إضافة المواصفات المهمة
        search_terms.extend(important_words[:3])
        search_terms.extend(analysis['key_specs'][:2])
        
        analysis['search_terms'] = search_terms[:4]  # أهم 4 مصطلحات
        
        return analysis

class SmartProfessionalComparator:
    """مقارن ذكي واحترافي للأسعار"""
    
    def __init__(self):
        self.analyzer = SmartProductAnalyzer()
        self.stats = {
            'total_comparisons': 0,
            'successful_comparisons': 0,
            'noon_successes': 0,
            'kanbkam_successes': 0,
            'avg_market_price_found': 0,
            'cache_hits': 0,
            'avg_comparison_time': 0
        }
        self.cache = {}
        self.last_search_time = 0
        self.min_search_delay = 2.0
    
    def build_smart_search_url(self, site: str, search_terms: list, category: str = 'general') -> str:
        """بناء رابط بحث ذكي ومحسن"""
        
        # تنظيف وتحسين مصطلحات البحث
        clean_terms = []
        for term in search_terms:
            if term and len(term) > 1:
                clean_terms.append(term.strip())
        
        search_query = ' '.join(clean_terms[:4])  # أهم 4 مصطلحات
        encoded_query = urllib.parse.quote(search_query)
        
        if site == 'noon':
            # رابط نون محسن مع فلترة حسب الفئة
            base_url = "https://www.noon.com/egypt-en/search/"
            if category == 'smartphones':
                return f"{base_url}?q={encoded_query}&category=electronics-mobiles"
            elif category == 'chargers':
                return f"{base_url}?q={encoded_query}&category=electronics-accessories"
            elif category == 'monitors' or category == 'televisions':
                return f"{base_url}?q={encoded_query}&category=electronics-computers"
            else:
                return f"{base_url}?q={encoded_query}"
        
        elif site == 'kanbkam':
            # رابط كان بكام محسن
            return f"https://www.kanbkam.com/ar/search?q={encoded_query}"
        
        return f"https://www.google.com/search?q={encoded_query}+سعر+مصر"
    
    async def smart_noon_search(self, product_analysis: dict) -> dict:
        """بحث ذكي في نون بناءً على تحليل المنتج"""
        
        result = {'prices': [], 'products_found': 0, 'avg_price': 0}
        
        try:
            search_url = self.build_smart_search_url('noon', product_analysis['search_terms'], product_analysis['category'])
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                
                page = await browser.new_page()
                
                print(f"      🌙 نون: {search_url}")
                
                await page.goto(search_url, timeout=8000)
                await page.wait_for_timeout(3000)
                
                # استخراج ذكي للأسعار والمنتجات
                noon_data = await page.evaluate("""
                    () => {
                        const data = {prices: [], products: [], titles: []};
                        
                        // البحث في عناصر المنتجات
                        const productElements = document.querySelectorAll('[data-qa*="product"], .productContainer, .product-item');
                        
                        productElements.forEach(element => {
                            // استخراج العنوان
                            const titleEl = element.querySelector('h3, .productName, [data-qa*="name"]');
                            const title = titleEl ? titleEl.textContent.trim() : '';
                            
                            // استخراج السعر
                            const priceEl = element.querySelector('[data-qa*="price"], .price, .priceNow');
                            if (priceEl) {
                                const priceText = priceEl.textContent || '';
                                const match = priceText.match(/([0-9,]+(?:\\.[0-9]+)?)/);
                                if (match) {
                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                    if (price >= 20 && price <= 200000) {
                                        data.prices.push(price);
                                        data.titles.push(title);
                                    }
                                }
                            }
                        });
                        
                        // البحث العام في النص إذا لم نجد منتجات
                        if (data.prices.length === 0) {
                            const bodyText = document.body.innerText || '';
                            const matches = bodyText.match(/([0-9,]+)\\s*(?:جنيه|EGP)/gi);
                            if (matches) {
                                matches.slice(0, 10).forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9]/g, ''));
                                    if (price >= 20 && price <= 200000) {
                                        data.prices.push(price);
                                    }
                                });
                            }
                        }
                        
                        return data;
                    }
                """)
                
                await browser.close()
                
                if noon_data['prices']:
                    # فلترة الأسعار وحساب المتوسط
                    prices = sorted(noon_data['prices'])
                    
                    # إزالة الأسعار الشاذة
                    if len(prices) > 4:
                        # إزالة أعلى وأقل 20%
                        remove_count = len(prices) // 5
                        prices = prices[remove_count:-remove_count] if remove_count > 0 else prices
                    
                    result['prices'] = prices
                    result['products_found'] = len(noon_data['titles'])
                    result['avg_price'] = statistics.mean(prices) if prices else 0
                    
                    self.stats['noon_successes'] += 1
                    print(f"         ✅ وجدت {len(prices)} أسعار، متوسط: {result['avg_price']:,.0f} EGP")
                    
                    # طباعة عينة من المنتجات الموجودة
                    if noon_data['titles']:
                        sample_titles = noon_data['titles'][:3]
                        for title in sample_titles:
                            if title:
                                print(f"         📱 {title[:50]}...")
                
        except Exception as e:
            print(f"         ❌ خطأ في نون: {e}")
        
        return result
    
    async def smart_kanbkam_search(self, product_analysis: dict) -> dict:
        """بحث ذكي في كان بكام"""
        
        result = {'prices': [], 'products_found': 0, 'avg_price': 0}
        
        try:
            search_url = self.build_smart_search_url('kanbkam', product_analysis['search_terms'])
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                
                page = await browser.new_page()
                
                print(f"      🏪 كان بكام: {search_url}")
                
                await page.goto(search_url, timeout=8000)
                await page.wait_for_timeout(2500)
                
                # استخراج الأسعار من كان بكام
                kanbkam_prices = await page.evaluate("""
                    () => {
                        const prices = [];
                        
                        // البحث في عناصر الأسعار
                        const priceElements = document.querySelectorAll('.price, .product-price, [class*="price"]');
                        priceElements.forEach(element => {
                            const text = element.textContent || '';
                            const match = text.match(/([0-9,]+(?:\\.[0-9]+)?)/);
                            if (match) {
                                const price = parseFloat(match[1].replace(/,/g, ''));
                                if (price >= 20 && price <= 200000) {
                                    prices.push(price);
                                }
                            }
                        });
                        
                        // البحث العام إذا لم نجد أسعار
                        if (prices.length === 0) {
                            const bodyText = document.body.innerText || '';
                            const matches = bodyText.match(/([0-9,]+)\\s*(?:جنيه|EGP|ج\\.م)/gi);
                            if (matches) {
                                matches.slice(0, 8).forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9]/g, ''));
                                    if (price >= 20 && price <= 200000) {
                                        prices.push(price);
                                    }
                                });
                            }
                        }
                        
                        return prices.sort((a, b) => a - b);
                    }
                """)
                
                await browser.close()
                
                if kanbkam_prices:
                    result['prices'] = kanbkam_prices
                    result['products_found'] = len(kanbkam_prices)
                    result['avg_price'] = statistics.mean(kanbkam_prices)
                    
                    self.stats['kanbkam_successes'] += 1
                    print(f"         ✅ وجدت {len(kanbkam_prices)} أسعار، متوسط: {result['avg_price']:,.0f} EGP")
                
        except Exception as e:
            print(f"         ❌ خطأ في كان بكام: {e}")
        
        return result
    
    async def professional_market_comparison(self, product_name: str, amazon_price: float) -> dict:
        """مقارنة احترافية وذكية مع السوق المصري"""
        
        # تحكم في السرعة
        current_time = time.time()
        if current_time - self.last_search_time < self.min_search_delay:
            await asyncio.sleep(self.min_search_delay - (current_time - self.last_search_time))
        self.last_search_time = time.time()
        
        # تحليل ذكي للمنتج
        product_analysis = self.analyzer.analyze_product_description(product_name)
        
        cache_key = f"smart_{'-'.join(product_analysis['search_terms'])}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🧠 تحليل احترافي: {product_name[:40]}...")
        print(f"   🏷️ العلامة: {product_analysis['brand']} | 📂 الفئة: {product_analysis['category']}")
        print(f"   🔍 مصطلحات البحث: {product_analysis['search_terms']}")
        print(f"   📊 ثقة التحليل: {product_analysis['confidence']}%")
        
        start_time = time.time()
        
        result = {
            'amazon_price': amazon_price,
            'market_prices': [],
            'noon_data': {},
            'kanbkam_data': {},
            'market_average': 0,
            'total_products_found': 0,
            'is_good_deal': False,
            'confidence': 50,
            'reason': 'تحليل السوق',
            'comparison_type': 'professional_analysis',
            'product_analysis': product_analysis
        }
        
        # البحث المتوازي في المواقع
        try:
            noon_task = self.smart_noon_search(product_analysis)
            kanbkam_task = self.smart_kanbkam_search(product_analysis)
            
            noon_data, kanbkam_data = await asyncio.gather(
                asyncio.wait_for(noon_task, timeout=10),
                asyncio.wait_for(kanbkam_task, timeout=10),
                return_exceptions=True
            )
            
            # معالجة نتائج نون
            if isinstance(noon_data, dict) and noon_data.get('prices'):
                result['noon_data'] = noon_data
                result['market_prices'].extend(noon_data['prices'])
                result['total_products_found'] += noon_data['products_found']
            
            # معالجة نتائج كان بكام
            if isinstance(kanbkam_data, dict) and kanbkam_data.get('prices'):
                result['kanbkam_data'] = kanbkam_data
                result['market_prices'].extend(kanbkam_data['prices'])
                result['total_products_found'] += kanbkam_data['products_found']
            
        except Exception as e:
            print(f"   ❌ خطأ في البحث المتوازي: {e}")
        
        # تحليل النتائج الاحترافي
        if result['market_prices']:
            # إزالة التكرار وفلترة
            unique_prices = sorted(list(set(result['market_prices'])))
            
            # فلترة احترافية للأسعار الشاذة
            if len(unique_prices) > 5:
                median_price = statistics.median(unique_prices)
                filtered_prices = []
                for price in unique_prices:
                    if 0.3 * median_price <= price <= 3 * median_price:
                        filtered_prices.append(price)
                
                if len(filtered_prices) >= 3:
                    unique_prices = filtered_prices
            
            result['market_prices'] = unique_prices
            
            if len(unique_prices) >= 2:
                # حساب متوسط السوق الحقيقي
                market_average = statistics.mean(unique_prices)
                market_min = min(unique_prices)
                market_max = max(unique_prices)
                
                result['market_average'] = market_average
                self.stats['avg_market_price_found'] += market_average
                
                # تحليل موقع أمازون احترافياً
                vs_average_percent = ((market_average - amazon_price) / market_average) * 100
                vs_min_percent = ((market_min - amazon_price) / market_min) * 100
                
                # حساب ترتيب أمازون
                cheaper_count = sum(1 for p in unique_prices if p > amazon_price)
                amazon_rank = len(unique_prices) - cheaper_count + 1
                
                # تحديد مستوى الصفقة بطريقة احترافية
                if amazon_price <= market_min:
                    result['confidence'] = 95
                    result['reason'] = f"🔥 الأرخص في السوق! أقل بـ {abs(vs_min_percent):.0f}% من أقل سعر"
                    result['is_good_deal'] = True
                elif amazon_rank == 2:
                    result['confidence'] = 90
                    result['reason'] = f"✅ ثاني أرخص في السوق من {len(unique_prices)} منتجات"
                    result['is_good_deal'] = True
                elif vs_average_percent > 25:
                    result['confidence'] = 85
                    result['reason'] = f"⚡ أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                    result['is_good_deal'] = True
                elif vs_average_percent > 15:
                    result['confidence'] = 80
                    result['reason'] = f"✅ أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                    result['is_good_deal'] = True
                elif vs_average_percent > 5:
                    result['confidence'] = 70
                    result['reason'] = f"💸 أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                    result['is_good_deal'] = True
                elif vs_average_percent > -10:
                    result['confidence'] = 65
                    result['reason'] = f"⚠️ قريب من متوسط السوق ({market_average:,.0f})"
                    result['is_good_deal'] = True
                else:
                    result['confidence'] = 45
                    result['reason'] = f"❌ أغلى بـ {abs(vs_average_percent):.0f}% من متوسط السوق"
                    result['is_good_deal'] = False
                
                result['comparison_type'] = 'professional_market_comparison'
                self.stats['successful_comparisons'] += 1
                
                # طباعة التحليل الاحترافي
                sites_info = []
                if result['noon_data'].get('prices'):
                    sites_info.append(f"نون({len(result['noon_data']['prices'])})")
                if result['kanbkam_data'].get('prices'):
                    sites_info.append(f"كان بكام({len(result['kanbkam_data']['prices'])})")
                
                print(f"   📊 تحليل احترافي للسوق المصري:")
                print(f"      💰 متوسط السوق: {market_average:,.0f} EGP")
                print(f"      📉 أقل سعر: {market_min:,.0f} EGP")
                print(f"      📈 أعلى سعر: {market_max:,.0f} EGP")
                print(f"      🎯 أمازون: {amazon_price:,.0f} EGP (ترتيب {amazon_rank} من {len(unique_prices)})")
                print(f"      🌐 المصادر: {', '.join(sites_info)}")
                print(f"      📱 منتجات موجودة: {result['total_products_found']}")
                print(f"   {result['reason']}")
                
            else:
                # منتج واحد فقط
                single_price = unique_prices[0]
                diff = ((single_price - amazon_price) / single_price) * 100
                result['market_average'] = single_price
                
                if diff > 15:
                    result['confidence'] = 80
                    result['reason'] = f"✅ أرخص بـ {diff:.0f}% من السوق"
                    result['is_good_deal'] = True
                elif diff > 0:
                    result['confidence'] = 70
                    result['reason'] = f"⚡ أرخص بـ {diff:.0f}% من السوق"
                    result['is_good_deal'] = True
                else:
                    result['confidence'] = 50
                    result['reason'] = f"⚠️ مساوي أو أغلى من السوق"
                    result['is_good_deal'] = False
                
                result['comparison_type'] = 'single_market_price'
        
        else:
            # لم نجد أسعار - تحليل بناءً على جودة المنتج
            if product_analysis['confidence'] >= 60:
                result['confidence'] = 60
                result['reason'] = f"⚠️ منتج جيد ({product_analysis['brand']}) - لم توجد أسعار للمقارنة"
                result['is_good_deal'] = True
            else:
                result['confidence'] = 40
                result['reason'] = f"❌ لم يتم العثور على أسعار للمقارنة"
                result['is_good_deal'] = False
            
            result['comparison_type'] = 'no_market_data'
        
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

# إنشاء المقارن الذكي والاحترافي
smart_comparator = SmartProfessionalComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع المقارنة الذكية والاحترافية"""
    
    def smart_compare_and_send():
        """مقارنة ذكية وإرسال"""
        
        if smart_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    smart_comparator.professional_market_comparison(
                        item.get('name', ''), new_price
                    )
                )
                
                # قبول المنتجات بناءً على التحليل الاحترافي
                if not comparison_result['is_good_deal'] or comparison_result['confidence'] < 50:
                    print(f"🚫 رفض احترافي: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    return
                
                # إضافة معلومات المقارنة الذكية
                item['smart_comparison'] = comparison_result
                item['market_confidence'] = comparison_result['confidence']
                item['market_reason'] = comparison_result['reason']
                item['market_average'] = comparison_result['market_average']
                item['comparison_type'] = comparison_result['comparison_type']
                item['product_analysis'] = comparison_result['product_analysis']
                item['total_products_found'] = comparison_result['total_products_found']
                
                print(f"✅ قبول احترافي: {item.get('name', '')[:35]}... - ثقة {comparison_result['confidence']}%")
                
            except Exception as e:
                print(f"⚠️ خطأ في المقارنة الذكية: {e}")
                return
            finally:
                try:
                    loop.close()
                except:
                    pass
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=smart_compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة ونتائج المقارنة الذكية"""
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
        market_reason = item.get('market_reason', '')
        market_confidence = item.get('market_confidence', 0)
        market_average = item.get('market_average', 0)
        comparison_type = item.get('comparison_type', 'unknown')
        product_analysis = item.get('product_analysis', {})
        total_products_found = item.get('total_products_found', 0)

        # عرض السعر الحالي فقط
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على نتيجة المقارنة الذكية
        if market_confidence >= 90:
            headline = "🔥 <b>BEST MARKET DEAL!</b> 🔥"
        elif market_confidence >= 80:
            headline = "✅ <b>EXCELLENT DEAL!</b>"
        elif market_confidence >= 70:
            headline = "⚡ <b>GREAT DEAL!</b>"
        elif market_confidence >= 60:
            headline = "💸 <b>GOOD DEAL!</b>"
        else:
            headline = "🛍️ <b>Fair Deal</b>"

        # معلومات المقارنة الذكية
        market_info = ""
        if market_reason:
            market_info = f"\n🎯 <b>Smart Analysis:</b> {market_reason}"
        
        # متوسط السوق الحقيقي
        market_avg_info = ""
        if market_average > 0:
            market_avg_info = f"\n📊 <b>Market Average:</b> {market_average:,.0f} EGP"
        
        # معلومات تحليل المنتج
        product_info = ""
        if product_analysis:
            brand = product_analysis.get('brand', 'unknown')
            category = product_analysis.get('category', 'general')
            if brand != 'unknown':
                product_info += f"\n🏷️ <b>Brand:</b> {brand.title()}"
            if category != 'general':
                product_info += f"\n📂 <b>Category:</b> {category.title()}"
        
        # معلومات المنتجات الموجودة
        products_info = ""
        if total_products_found > 0:
            products_info = f"\n🔍 <b>Products Found:</b> {total_products_found} similar products"
        
        # معلومات نوع التحليل
        method_info = ""
        if comparison_type == 'professional_market_comparison':
            method_info = f"\n📊 <b>Method:</b> Professional Market Analysis"
        elif comparison_type == 'single_market_price':
            method_info = f"\n📊 <b>Method:</b> Single Market Reference"
        elif comparison_type == 'no_market_data':
            method_info = f"\n📊 <b>Method:</b> Product Quality Analysis"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {market_confidence}%" if market_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 <b>Amazon Price:</b> {price_now}{confidence_row}{market_info}{market_avg_info}{product_info}{products_info}{method_info}

🧠 <b>Smart Professional Market Analysis</b>
"""

        # أزرار محسنة مع روابط ذكية
        search_terms = product_analysis.get('search_terms', []) if product_analysis else []
        if not search_terms:
            # استخراج بسيط إذا لم يكن هناك تحليل
            search_terms = product_name.split()[:3]
        
        search_query = ' '.join(search_terms)
        encoded_query = urllib.parse.quote(search_query)
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛍️ Buy on Amazon", "url": url}],
                [
                    {"text": "🌙 Smart Noon Search", "url": f"https://www.noon.com/egypt-en/search/?q={encoded_query}"},
                    {"text": "🌐 Google Search", "url": f"https://www.google.com/search?q={encoded_query}+سعر+مصر"}
                ],
                [{"text": "🏪 كان بكام", "url": f"https://www.kanbkam.com/ar/search?q={encoded_query}"}]
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
            method_text = "تحليل احترافي" if comparison_type == 'professional_market_comparison' else "تحليل ذكي"
            print(f"✅ تم إرسال تنبيه لـ {sent_count} مستخدم - ثقة {market_confidence}% ({method_text})")

    except Exception as e:
        print("❌ Telegram Error:", e)

# باقي الدوال الأساسية (مختصرة للمساحة)
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

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة مع المقارنة الذكية"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[SMART PROFESSIONAL]" if smart_comparison_enabled[0] else ""
            log_fn(f"🧠 {mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:10]:  # 10 منتجات للتوازن مع المقارنة المتقدمة
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
                if not price or price < 50:  # حد أدنى أعلى للجودة
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

                # إرسال للمقارنة الذكية
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
            log_fn(f"[Page {page_num}] 🧠 {new_count} NEW products")
        
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
    
    smart_mode = "SMART PROFESSIONAL ON" if smart_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🧠 Smart Professional Start - New Products: {auto_mode}, Smart: {smart_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Smart professional scraping {sec_name}...", "🧠")
                        for page_num in range(1, pages + 1):
                            if stop_flag.get("stop"):
                                break
                            await scrape_single_page(
                                sec_name, sec_url, page_num, db,
                                log_fn=lambda m: log(m, "🧠"),
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
                            log_fn=lambda m: log(m, "🧠"),
                            discount_alert_cb=add_alert_data,
                            discount_threshold=ALERT_DISCOUNT
                        )
                        update_progress(page_num / pages)
            
            loop.run_until_complete(scrape_all())
            
        except Exception as e:
            log(f"❌ Scraper error: {e}")
        finally:
            save_db()
            log("✅ Smart Professional Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Smart Professional Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    if smart_comparison_enabled[0]:
        stats = smart_comparator.stats
        log(f"🧠 Smart Professional Stats:")
        log(f"   📊 Total Comparisons: {stats['total_comparisons']}")
        log(f"   ✅ Successful Comparisons: {stats['successful_comparisons']}")
        log(f"   🌙 Noon Successes: {stats['noon_successes']}")
        log(f"   🏪 Kanbkam Successes: {stats['kanbkam_successes']}")
        log(f"   💰 Avg Market Price Found: {stats['avg_market_price_found']/max(stats['successful_comparisons'],1):,.0f} EGP")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ⏱️ Avg Comparison Time: {stats['avg_comparison_time']:.1f}s")
        
        if stats['total_comparisons'] > 0:
            success_rate = (stats['successful_comparisons'] / stats['total_comparisons']) * 100
            noon_rate = (stats['noon_successes'] / stats['total_comparisons']) * 100
            kanbkam_rate = (stats['kanbkam_successes'] / stats['total_comparisons']) * 100
            log(f"   📈 Success Rate: {success_rate:.1f}%")
            log(f"   📈 Noon Success Rate: {noon_rate:.1f}%")
            log(f"   📈 Kanbkam Success Rate: {kanbkam_rate:.1f}%")

def toggle_smart_comparison():
    smart_comparison_enabled[0] = not smart_comparison_enabled[0]
    status = "SMART PROFESSIONAL ON" if smart_comparison_enabled[0] else "OFF"
    log(f"🧠 Smart Professional: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Amazon Price", "Market Average", "Confidence", "Analysis", "Products Found"])
        for asin, item in db.items():
            amazon_price = item.get('price', 0)
            market_avg = item.get('market_average', 0)
            confidence = item.get('market_confidence', 0)
            reason = item.get('market_reason', '')
            products_found = item.get('total_products_found', 0)
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], amazon_price, market_avg, confidence, reason, products_found])
    log("Exported to CSV with smart professional analysis.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# الواجهة الأصلية
root = ctk.CTk()
root.title("LAQTA - Smart Professional Analysis")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Smart Professional Market Analysis", 
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

smart_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🧠 Smart Pro", font=("Arial", 13), 
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

start_btn = ctk.CTkButton(buttons_frame, text="🧠 Smart Pro Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Smart Stats", command=show_stats, width=btn_w, height=btn_h,
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

log("🧠 LAQTA Smart Professional Analysis System started!", "🚀")
log("🔍 Product Analysis: Smart description parsing + category detection", "✨")
log("🌙 Noon + 🏪 Kanbkam: Professional market comparison with real averages", "📊")
log("📸 Telegram: ON - with photos and professional analysis", "📱")
log("⚡ Speed: 2s between searches, smart caching, optimized URLs", "🏃")
log("🎯 Strategy: Analyze product → Smart search → Calculate real market average", "💡")
log("📱 Expected: PROFESSIONAL market analysis with real price comparisons!", "🏆")

root.mainloop()
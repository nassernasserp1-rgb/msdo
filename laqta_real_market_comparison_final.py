#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAQTA - مقارنة السوق المصري الحقيقية
مقارنة مع نون + برايسنا + كان بكام + متوسط السوق
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

# نظام مقارنة السوق المصري
class EgyptianMarketComparator:
    """مقارن السوق المصري - نون + برايسنا + كان بكام"""
    
    def __init__(self):
        self.stats = {
            'total_comparisons': 0,
            'successful_comparisons': 0,
            'noon_successes': 0,
            'pricesna_successes': 0,
            'kanbkam_successes': 0,
            'comparison_failures': 0,
            'cache_hits': 0,
            'avg_comparison_time': 0
        }
        self.cache = {}
        self.last_search_time = 0
        self.min_search_delay = 2.0
        
    def extract_product_keywords(self, product_name: str) -> str:
        """استخراج الكلمات المهمة للبحث الدقيق"""
        
        # إزالة الكلمات غير المفيدة
        stop_words = [
            'new', 'original', 'pack', 'set', 'piece', 'amazon', 'choice',
            'brand', 'compatible', 'with', 'for', 'الجديد', 'أصلي', 'حزمة',
            'ml', 'gm', 'kg', 'cm', 'mm', 'inch'
        ]
        
        # استخراج العلامة التجارية والكلمات المهمة
        words = []
        product_words = re.findall(r'\b[a-zA-Z]{2,}\b', product_name)
        
        for word in product_words[:5]:  # أول 5 كلمات إنجليزية
            clean_word = word.lower()
            if len(clean_word) > 2 and clean_word not in stop_words:
                words.append(clean_word)
        
        # إضافة الأرقام المهمة (مثل حجم المنتج)
        numbers = re.findall(r'\b\d+(?:ml|gm|gb|tb)\b', product_name.lower())
        words.extend(numbers[:2])
        
        return ' '.join(words[:4]) if words else product_name.split()[0]
    
    async def search_noon_prices(self, search_term: str) -> list:
        """بحث دقيق في نون"""
        prices = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                
                page = await browser.new_page()
                
                # رابط نون محسن للبحث الدقيق
                noon_url = f"https://www.noon.com/egypt-en/search/?q={search_term.replace(' ', '%20')}"
                
                await page.goto(noon_url, timeout=8000)
                await page.wait_for_timeout(2500)
                
                # استخراج الأسعار من نون
                noon_prices = await page.evaluate("""
                    () => {
                        const prices = new Set();
                        
                        // البحث في عناصر الأسعار المختلفة
                        const selectors = [
                            '.priceNow', '.price-now', '.final-price', 
                            '[data-qa="product-price"]', '.productPrice',
                            '[class*="price"]', '[class*="Price"]'
                        ];
                        
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(element => {
                                const text = element.textContent || '';
                                const match = text.match(/([0-9,]+(?:\\.[0-9]+)?)/);
                                if (match) {
                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                    if (price >= 10 && price <= 200000) {
                                        prices.add(price);
                                    }
                                }
                            });
                        }
                        
                        // البحث في النص العام
                        if (prices.size === 0) {
                            const bodyText = document.body.innerText || '';
                            const matches = bodyText.match(/([0-9,]+)\\s*(?:جنيه|EGP|ج\\.م)/gi);
                            if (matches) {
                                matches.slice(0, 10).forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9]/g, ''));
                                    if (price >= 10 && price <= 200000) {
                                        prices.add(price);
                                    }
                                });
                            }
                        }
                        
                        return Array.from(prices).sort((a, b) => a - b).slice(0, 10);
                    }
                """)
                
                await browser.close()
                
                if noon_prices:
                    prices = noon_prices
                    self.stats['noon_successes'] += 1
                    print(f"      🌙 نون: {len(prices)} أسعار - من {min(prices):,.0f} إلى {max(prices):,.0f}")
                
        except Exception as e:
            print(f"      ⚠️ نون: خطأ - {e}")
        
        return prices
    
    async def search_pricesna_prices(self, search_term: str) -> list:
        """بحث في موقع برايسنا"""
        prices = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                
                page = await browser.new_page()
                
                # رابط برايسنا
                pricesna_url = f"https://pricesna.com/en/search?q={search_term.replace(' ', '+')}"
                
                await page.goto(pricesna_url, timeout=8000)
                await page.wait_for_timeout(2500)
                
                # استخراج الأسعار من برايسنا
                pricesna_prices = await page.evaluate("""
                    () => {
                        const prices = new Set();
                        
                        // البحث في عناصر الأسعار
                        const selectors = [
                            '.price', '.product-price', '.current-price',
                            '[class*="price"]', '[class*="Price"]',
                            '.cost', '.amount'
                        ];
                        
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(element => {
                                const text = element.textContent || '';
                                const match = text.match(/([0-9,]+(?:\\.[0-9]+)?)/);
                                if (match) {
                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                    if (price >= 10 && price <= 200000) {
                                        prices.add(price);
                                    }
                                }
                            });
                        }
                        
                        // البحث في النص العام
                        if (prices.size === 0) {
                            const bodyText = document.body.innerText || '';
                            const matches = bodyText.match(/([0-9,]+)\\s*(?:EGP|جنيه|ج\\.م|LE)/gi);
                            if (matches) {
                                matches.slice(0, 8).forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9]/g, ''));
                                    if (price >= 10 && price <= 200000) {
                                        prices.add(price);
                                    }
                                });
                            }
                        }
                        
                        return Array.from(prices).sort((a, b) => a - b).slice(0, 8);
                    }
                """)
                
                await browser.close()
                
                if pricesna_prices:
                    prices = pricesna_prices
                    self.stats['pricesna_successes'] += 1
                    print(f"      💰 برايسنا: {len(prices)} أسعار - من {min(prices):,.0f} إلى {max(prices):,.0f}")
                
        except Exception as e:
            print(f"      ⚠️ برايسنا: خطأ - {e}")
        
        return prices
    
    async def search_kanbkam_prices(self, search_term: str) -> list:
        """بحث في موقع كان بكام"""
        prices = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                
                page = await browser.new_page()
                
                # رابط كان بكام
                kanbkam_url = f"https://www.kanbkam.com/search?q={search_term.replace(' ', '+')}"
                
                await page.goto(kanbkam_url, timeout=8000)
                await page.wait_for_timeout(2500)
                
                # استخراج الأسعار من كان بكام
                kanbkam_prices = await page.evaluate("""
                    () => {
                        const prices = new Set();
                        
                        // البحث في عناصر الأسعار
                        const selectors = [
                            '.price', '.product-price', '.item-price',
                            '[class*="price"]', '[class*="Price"]',
                            '.cost', '.value'
                        ];
                        
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(element => {
                                const text = element.textContent || '';
                                const match = text.match(/([0-9,]+(?:\\.[0-9]+)?)/);
                                if (match) {
                                    const price = parseFloat(match[1].replace(/,/g, ''));
                                    if (price >= 10 && price <= 200000) {
                                        prices.add(price);
                                    }
                                }
                            });
                        }
                        
                        // البحث في النص العام
                        if (prices.size === 0) {
                            const bodyText = document.body.innerText || '';
                            const matches = bodyText.match(/([0-9,]+)\\s*(?:جنيه|EGP|ج\\.م|LE)/gi);
                            if (matches) {
                                matches.slice(0, 6).forEach(match => {
                                    const price = parseFloat(match.replace(/[^0-9]/g, ''));
                                    if (price >= 10 && price <= 200000) {
                                        prices.add(price);
                                    }
                                });
                            }
                        }
                        
                        return Array.from(prices).sort((a, b) => a - b).slice(0, 6);
                    }
                """)
                
                await browser.close()
                
                if kanbkam_prices:
                    prices = kanbkam_prices
                    self.stats['kanbkam_successes'] += 1
                    print(f"      🏪 كان بكام: {len(prices)} أسعار - من {min(prices):,.0f} إلى {max(prices):,.0f}")
                
        except Exception as e:
            print(f"      ⚠️ كان بكام: خطأ - {e}")
        
        return prices
    
    async def compare_with_egyptian_market(self, product_name: str, amazon_price: float) -> dict:
        """مقارنة مع السوق المصري"""
        
        # تحكم في السرعة
        current_time = time.time()
        if current_time - self.last_search_time < self.min_search_delay:
            await asyncio.sleep(self.min_search_delay - (current_time - self.last_search_time))
        self.last_search_time = time.time()
        
        search_term = self.extract_product_keywords(product_name)
        cache_key = f"market_{search_term}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        print(f"🏪 مقارنة السوق المصري: {product_name[:40]}...")
        print(f"   🔎 كلمات البحث: '{search_term}'")
        
        start_time = time.time()
        
        result = {
            'amazon_price': amazon_price,
            'market_prices': [],
            'noon_prices': [],
            'pricesna_prices': [],
            'kanbkam_prices': [],
            'market_average': 0,
            'is_good_deal': False,
            'confidence': 50,
            'reason': 'لم يتم العثور على أسعار في السوق',
            'comparison_type': 'no_market_data',
            'sites_checked': 3,
            'sites_found': 0,
            'amazon_vs_market': 0
        }
        
        # البحث المتوازي في المواقع الثلاثة
        try:
            noon_task = self.search_noon_prices(search_term)
            pricesna_task = self.search_pricesna_prices(search_term)
            kanbkam_task = self.search_kanbkam_prices(search_term)
            
            # انتظار النتائج مع timeout
            noon_prices, pricesna_prices, kanbkam_prices = await asyncio.gather(
                asyncio.wait_for(noon_task, timeout=10),
                asyncio.wait_for(pricesna_task, timeout=10),
                asyncio.wait_for(kanbkam_task, timeout=10),
                return_exceptions=True
            )
            
            # معالجة النتائج
            if isinstance(noon_prices, list) and noon_prices:
                result['noon_prices'] = noon_prices
                result['market_prices'].extend(noon_prices)
                result['sites_found'] += 1
            
            if isinstance(pricesna_prices, list) and pricesna_prices:
                result['pricesna_prices'] = pricesna_prices
                result['market_prices'].extend(pricesna_prices)
                result['sites_found'] += 1
            
            if isinstance(kanbkam_prices, list) and kanbkam_prices:
                result['kanbkam_prices'] = kanbkam_prices
                result['market_prices'].extend(kanbkam_prices)
                result['sites_found'] += 1
            
        except Exception as e:
            print(f"   ❌ خطأ في البحث المتوازي: {e}")
        
        # تحليل النتائج
        if result['market_prices']:
            # إزالة التكرار وفلترة الأسعار الغريبة
            unique_prices = sorted(list(set(result['market_prices'])))
            
            # فلترة الأسعار الغريبة
            if len(unique_prices) > 4:
                median_price = statistics.median(unique_prices)
                filtered_prices = []
                for price in unique_prices:
                    if 0.1 * median_price <= price <= 10 * median_price:
                        filtered_prices.append(price)
                
                if len(filtered_prices) >= 3:
                    unique_prices = filtered_prices
            
            result['market_prices'] = unique_prices
            
            if len(unique_prices) >= 2:
                # حساب متوسط السوق
                market_average = statistics.mean(unique_prices)
                market_min = min(unique_prices)
                market_max = max(unique_prices)
                
                result['market_average'] = market_average
                
                # حساب موقع أمازون مقارنة بالسوق
                vs_average_percent = ((market_average - amazon_price) / market_average) * 100
                vs_min_percent = ((market_min - amazon_price) / market_min) * 100
                
                result['amazon_vs_market'] = vs_average_percent
                
                # تحديد مستوى الصفقة بناءً على المقارنة الحقيقية
                if amazon_price <= market_min:
                    result['confidence'] = 95
                    result['reason'] = f"🔥 أرخص من كل السوق! أقل بـ {abs(vs_min_percent):.0f}% من أقل سعر"
                    result['is_good_deal'] = True
                elif vs_average_percent > 25:
                    result['confidence'] = 90
                    result['reason'] = f"✅ أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                    result['is_good_deal'] = True
                elif vs_average_percent > 15:
                    result['confidence'] = 80
                    result['reason'] = f"⚡ أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                    result['is_good_deal'] = True
                elif vs_average_percent > 5:
                    result['confidence'] = 70
                    result['reason'] = f"💸 أرخص بـ {vs_average_percent:.0f}% من متوسط السوق"
                    result['is_good_deal'] = True
                elif vs_average_percent > -10:
                    result['confidence'] = 60
                    result['reason'] = f"⚠️ قريب من متوسط السوق ({market_average:,.0f})"
                    result['is_good_deal'] = True
                else:
                    result['confidence'] = 40
                    result['reason'] = f"❌ أغلى بـ {abs(vs_average_percent):.0f}% من متوسط السوق"
                    result['is_good_deal'] = False
                
                result['comparison_type'] = 'market_comparison'
                self.stats['successful_comparisons'] += 1
                
                # طباعة النتائج
                sites_info = []
                if result['noon_prices']:
                    sites_info.append(f"نون({len(result['noon_prices'])})")
                if result['pricesna_prices']:
                    sites_info.append(f"برايسنا({len(result['pricesna_prices'])})")
                if result['kanbkam_prices']:
                    sites_info.append(f"كان بكام({len(result['kanbkam_prices'])})")
                
                print(f"   📊 مقارنة السوق المصري مع {', '.join(sites_info)}:")
                print(f"      💰 متوسط السوق: {market_average:,.0f} EGP")
                print(f"      📉 أقل سعر في السوق: {market_min:,.0f} EGP")
                print(f"      📈 أعلى سعر في السوق: {market_max:,.0f} EGP")
                print(f"      🎯 أمازون: {amazon_price:,.0f} EGP")
                print(f"   {result['reason']}")
                
            else:
                # سعر واحد فقط في السوق
                market_price = unique_prices[0]
                diff = ((market_price - amazon_price) / market_price) * 100
                
                result['market_average'] = market_price
                result['amazon_vs_market'] = diff
                
                if diff > 15:
                    result['confidence'] = 80
                    result['reason'] = f"✅ أرخص بـ {diff:.0f}% من السوق ({market_price:,.0f})"
                    result['is_good_deal'] = True
                elif diff > 0:
                    result['confidence'] = 70
                    result['reason'] = f"⚡ أرخص بـ {diff:.0f}% من السوق"
                    result['is_good_deal'] = True
                else:
                    result['confidence'] = 50
                    result['reason'] = f"⚠️ أغلى من السوق ({market_price:,.0f})"
                    result['is_good_deal'] = False
                
                result['comparison_type'] = 'single_market_price'
        
        else:
            # لم نجد أسعار في السوق - رفض
            result['confidence'] = 30
            result['reason'] = f"❌ لم يتم العثور على أسعار في السوق للمقارنة"
            result['is_good_deal'] = False
            result['comparison_type'] = 'no_market_data'
            self.stats['comparison_failures'] += 1
        
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

# إنشاء مقارن السوق المصري
market_comparator = EgyptianMarketComparator()

def send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه تليجرام مع مقارنة السوق المصري"""
    
    def compare_and_send():
        """مقارنة مع السوق وإرسال"""
        
        if market_comparison_enabled[0]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                comparison_result = loop.run_until_complete(
                    market_comparator.compare_with_egyptian_market(
                        item.get('name', ''), new_price
                    )
                )
                
                # رفض الصفقات الضعيفة بناءً على مقارنة السوق
                if not comparison_result['is_good_deal']:
                    print(f"🚫 رفض: {item.get('name', '')[:35]}... - {comparison_result['reason']}")
                    return
                
                # إضافة معلومات مقارنة السوق
                item['market_comparison'] = comparison_result
                item['market_confidence'] = comparison_result['confidence']
                item['market_reason'] = comparison_result['reason']
                item['market_average'] = comparison_result['market_average']
                item['amazon_vs_market'] = comparison_result['amazon_vs_market']
                item['comparison_type'] = comparison_result['comparison_type']
                item['noon_prices'] = comparison_result['noon_prices']
                item['pricesna_prices'] = comparison_result['pricesna_prices']
                item['kanbkam_prices'] = comparison_result['kanbkam_prices']
                
                print(f"✅ قبول: {item.get('name', '')[:35]}... - ثقة {comparison_result['confidence']}%")
                
            except Exception as e:
                print(f"⚠️ خطأ في مقارنة السوق: {e}")
                # في حالة الخطأ، نرفض المنتج
                return
            finally:
                loop.close()
        
        # إرسال الرسالة مع الصورة
        send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)
    
    threading.Thread(target=compare_and_send, daemon=True).start()

def send_actual_telegram_alert(item, old_price, new_price, discount_percent, drop_detected):
    """إرسال تنبيه مع الصورة ونتائج مقارنة السوق"""
    try:
        with open("telegram_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        bot_token = cfg["bot_token"]
        users = cfg["users"]

        product_name = item.get('name', 'No name')
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'Unknown')
        
        # معلومات مقارنة السوق
        market_reason = item.get('market_reason', '')
        market_confidence = item.get('market_confidence', 0)
        market_average = item.get('market_average', 0)
        amazon_vs_market = item.get('amazon_vs_market', 0)
        comparison_type = item.get('comparison_type', 'unknown')
        
        # الأسعار من المواقع المختلفة
        noon_prices = item.get('noon_prices', [])
        pricesna_prices = item.get('pricesna_prices', [])
        kanbkam_prices = item.get('kanbkam_prices', [])

        # عرض السعر الحالي فقط (بدون السعر المشطوب)
        price_now = f"<b>{int(new_price):,} EGP</b>"

        # عنوان بناءً على نتيجة مقارنة السوق
        if market_confidence >= 90:
            headline = "🔥 <b>BEST DEAL IN MARKET!</b> 🔥"
        elif market_confidence >= 80:
            headline = "✅ <b>GREAT MARKET DEAL!</b>"
        elif market_confidence >= 70:
            headline = "⚡ <b>GOOD MARKET DEAL!</b>"
        elif market_confidence >= 60:
            headline = "💸 <b>Fair Market Deal</b>"
        else:
            headline = "🛍️ <b>Market Deal</b>"

        # معلومات مقارنة السوق
        market_info = ""
        if market_reason:
            market_info = f"\n🏪 <b>Market Analysis:</b> {market_reason}"
        
        # متوسط السوق
        market_avg_info = ""
        if market_average > 0:
            market_avg_info = f"\n📊 <b>Market Average:</b> {market_average:,.0f} EGP"
        
        # تفاصيل المواقع التي تم فحصها
        sites_info = ""
        sites_checked = []
        if noon_prices:
            sites_checked.append(f"Noon({len(noon_prices)})")
        if pricesna_prices:
            sites_checked.append(f"Pricesna({len(pricesna_prices)})")
        if kanbkam_prices:
            sites_checked.append(f"Kanbkam({len(kanbkam_prices)})")
        
        if sites_checked:
            sites_info = f"\n🔍 <b>Market Check:</b> {', '.join(sites_checked)}"
        
        # معلومات نوع المقارنة
        method_info = ""
        if comparison_type == 'market_comparison':
            method_info = f"\n📊 <b>Method:</b> Egyptian Market Comparison"
        elif comparison_type == 'single_market_price':
            method_info = f"\n📊 <b>Method:</b> Single Market Price"
        elif comparison_type == 'no_market_data':
            method_info = f"\n📊 <b>Method:</b> No Market Data Found"
        
        confidence_row = f"\n📈 <b>Confidence:</b> {market_confidence}%" if market_confidence > 0 else ""

        msg = f"""{headline}

<b>{product_name}</b>

🔗 <a href="{url}">Buy on Amazon</a>
📦 <b>Section:</b> <code>{section}</code>

💰 <b>Amazon Price:</b> {price_now}{confidence_row}{market_info}{market_avg_info}{sites_info}{method_info}

🏪 <b>Real Egyptian Market Comparison</b>
"""

        # أزرار محسنة (بدون جوميا + إضافة كان بكام + بحث ويب)
        # استخراج كلمات البحث الدقيقة
        search_keywords = market_comparator.extract_product_keywords(product_name)
        
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
            method_text = "مقارنة السوق" if comparison_type == 'market_comparison' else "تحليل السوق"
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
    """إضافة بيانات التنبيه مع مقارنة السوق المصري"""
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
    
    # إرسال مع مقارنة السوق المصري
    if telegram_alerts_enabled[0]:
        send_telegram_alert(item, old_price, new_price, discount_percent, drop_detected)

def parse_egp_price(text):
    import re
    m = re.search(r'(\d[\d,\.]*)', text.replace(",", ""))
    return float(m.group(1)) if m else None

# دالة السكرابة
async def scrape_single_page(section, section_url, page_num, db, log_fn=None, discount_alert_cb=None, discount_threshold=25):
    """سكرابة صفحة واحدة مع مقارنة السوق المصري"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-images', '--disable-javascript']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        url = section_url.format(page_num)
        
        if log_fn:
            mode = "[MARKET COMPARISON]" if market_comparison_enabled[0] else ""
            log_fn(f"🏪 {mode} Scraping: {section}, page {page_num}")
        
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(1000)
        except Exception as e:
            await browser.close()
            return 0

        items = await page.query_selector_all('div.s-result-item[data-asin][data-component-type="s-search-result"]')
        new_count = 0

        for item in items[:10]:  # 10 منتجات للتوازن مع المقارنة
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
                if not price or price < 25:
                    continue

                # البحث عن السعر المشطوب (للمرجع فقط، لا نعتمد عليه)
                strike_el = await item.query_selector('.a-price.a-text-price .a-offscreen')
                strike_price = None
                if strike_el:
                    strike_txt = await strike_el.inner_text()
                    strike_price = parse_egp_price(strike_txt)

                # حساب نسبة الخصم (للمرجع فقط)
                discount_percent = 0
                if strike_price and price and strike_price > price:
                    discount_percent = ((strike_price - price) / strike_price) * 100

                # إرسال للمقارنة (بغض النظر عن الخصم - المقارنة ستحدد)
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
    
    market_mode = "MARKET COMPARISON ON" if market_comparison_enabled[0] else "OFF"
    auto_mode = "ON" if auto_new_products_mode[0] else "OFF"
    log(f"🏪 Market Comparison Start - New Products: {auto_mode}, Market: {market_mode}")
    
    def scraper_thread():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        try:
            async def scrape_all():
                if section == "All Sections":
                    for sec_name, sec_url in CATEGORIES.items():
                        if stop_flag.get("stop"):
                            break
                        log(f"Market comparison scraping {sec_name}...", "🏪")
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
            log("✅ Market Comparison Done.")
            running[0] = False
    
    threading.Thread(target=scraper_thread, daemon=True).start()

def stop_scraping():
    stop_flag["stop"] = True
    log("🛑 Market Comparison Stopped.")

def show_stats():
    total = len(db)
    log(f"🔢 Products: {total:,}")
    
    if market_comparison_enabled[0]:
        stats = market_comparator.stats
        log(f"🏪 Egyptian Market Stats:")
        log(f"   📊 Total Comparisons: {stats['total_comparisons']}")
        log(f"   ✅ Successful Comparisons: {stats['successful_comparisons']}")
        log(f"   🌙 Noon Successes: {stats['noon_successes']}")
        log(f"   💰 Pricesna Successes: {stats['pricesna_successes']}")
        log(f"   🏪 Kanbkam Successes: {stats['kanbkam_successes']}")
        log(f"   ❌ Comparison Failures: {stats['comparison_failures']}")
        log(f"   🧠 Cache Hits: {stats['cache_hits']}")
        log(f"   ⏱️ Avg Comparison Time: {stats['avg_comparison_time']:.1f}s")
        
        if stats['total_comparisons'] > 0:
            success_rate = (stats['successful_comparisons'] / stats['total_comparisons']) * 100
            noon_rate = (stats['noon_successes'] / stats['total_comparisons']) * 100
            pricesna_rate = (stats['pricesna_successes'] / stats['total_comparisons']) * 100
            kanbkam_rate = (stats['kanbkam_successes'] / stats['total_comparisons']) * 100
            log(f"   📈 Success Rate: {success_rate:.1f}%")
            log(f"   📈 Noon Success Rate: {noon_rate:.1f}%")
            log(f"   📈 Pricesna Success Rate: {pricesna_rate:.1f}%")
            log(f"   📈 Kanbkam Success Rate: {kanbkam_rate:.1f}%")

def toggle_market_comparison():
    market_comparison_enabled[0] = not market_comparison_enabled[0]
    status = "MARKET COMPARISON ON" if market_comparison_enabled[0] else "OFF"
    log(f"🏪 Market Comparison: {status}")

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
        writer.writerow(["ASIN", "Name", "Section", "URL", "Image", "Amazon Price", "Market Average", "Confidence", "Market Reason"])
        for asin, item in db.items():
            amazon_price = item.get('price', 0)
            market_avg = item.get('market_average', 0)
            confidence = item.get('market_confidence', 0)
            reason = item.get('market_reason', '')
            writer.writerow([asin, item["name"], item["section"], item["url"], item["img"], amazon_price, market_avg, confidence, reason])
    log("Exported to CSV with market comparison data.", "📁")

def set_min_discount(val):
    global ALERT_DISCOUNT
    ALERT_DISCOUNT = int(float(val))
    min_discount_label.configure(text=f"Min: {ALERT_DISCOUNT}%")

# الواجهة الأصلية
root = ctk.CTk()
root.title("LAQTA - Egyptian Market Comparison")
root.geometry("1550x950")
root.minsize(1300, 700)
root.rowconfigure(4, weight=1)
root.columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(root, text="LAQTA", font=("SST Arabic Medium", 55), text_color="#54fac8")
title_label.grid(row=0, column=0, padx=8, pady=(15, 5), sticky="ew")

subtitle_label = ctk.CTkLabel(root, text="Amazon Egypt Products Scraper - Egyptian Market Comparison", 
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

market_comparison_chk = ctk.CTkCheckBox(controls_frame, text="🏪 Market Compare", font=("Arial", 13), 
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

start_btn = ctk.CTkButton(buttons_frame, text="🏪 Market Start", command=start_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#4CAF50", hover_color="#45a049", text_color="#ffffff")
start_btn.grid(row=0, column=0, padx=5, pady=6, sticky="ew")

stop_btn = ctk.CTkButton(buttons_frame, text="⏹️ Stop", command=stop_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#f44336", hover_color="#da190b", text_color="#ffffff")
stop_btn.grid(row=0, column=1, padx=5, pady=6, sticky="ew")

resume_btn = ctk.CTkButton(buttons_frame, text="🔁 Resume", command=resume_scraping, width=btn_w, height=btn_h,
    font=btn_font, fg_color="#2196F3", hover_color="#0b7dda", text_color="#ffffff")
resume_btn.grid(row=0, column=2, padx=5, pady=6, sticky="ew")

stats_btn = ctk.CTkButton(buttons_frame, text="📊 Market Stats", command=show_stats, width=btn_w, height=btn_h,
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

log("🏪 LAQTA Egyptian Market Comparison System started!", "🚀")
log("🌙 Noon + 💰 Pricesna + 🏪 Kanbkam: Real Egyptian market comparison", "✨")
log("📸 Telegram: ON - with photos and market analysis", "📱")
log("⚡ Speed: 2s between searches, 8s timeout per site", "🏃")
log("🎯 Strategy: Compare with 3 Egyptian sites, calculate market average", "💡")
log("📱 Expected: REAL market comparisons based on actual prices!", "🏆")

root.mainloop()
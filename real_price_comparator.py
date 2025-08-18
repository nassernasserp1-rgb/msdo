#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مقارن الأسعار الحقيقي
بحث حقيقي في المواقع المصرية بدون خداع
"""

import asyncio
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright
import statistics

class RealPriceComparator:
    """مقارن الأسعار الحقيقي - بحث فعلي في المواقع المصرية"""
    
    def __init__(self):
        self.stats = {
            'total_comparisons': 0,
            'successful_comparisons': 0,
            'sites_checked': 0,
            'sites_successful': 0,
            'real_prices_found': 0,
            'comparison_errors': 0
        }
        
        # المواقع المصرية الحقيقية اللي بتشتغل فعلاً
        self.real_egyptian_sites = {
            'jumia': {
                'url': 'https://www.jumia.com.eg/catalog/?q={}',
                'name': 'جوميا',
                'price_selectors': ['.prc', '.price', '.current-price'],
                'working': True,
                'timeout': 8000
            },
            'noon': {
                'url': 'https://www.noon.com/egypt-en/search/?q={}',
                'name': 'نون',
                'price_selectors': ['.priceNow', '.price-now', '.final-price'],
                'working': True,
                'timeout': 8000
            }
        }
        
        # كاش للنتائج
        self.cache = {}
    
    def simplify_product_name(self, product_name: str) -> str:
        """تبسيط اسم المنتج للبحث الحقيقي"""
        
        # استخراج العلامة التجارية
        brands = ['samsung', 'xiaomi', 'apple', 'sony', 'lg', 'anker', 'joyroom', 'vaseline', 'nivea', 'axe', 'care']
        
        name_lower = product_name.lower()
        brand_found = ""
        
        for brand in brands:
            if brand in name_lower:
                brand_found = brand
                break
        
        # استخراج كلمات مهمة
        important_words = []
        for word in product_name.split():
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if (len(clean_word) > 3 and 
                clean_word not in ['amazon', 'choice', 'brand', 'series', 'with', 'from']):
                important_words.append(clean_word)
            if len(important_words) >= 3:
                break
        
        # بناء مصطلح البحث
        if brand_found:
            search_term = brand_found
            if important_words:
                search_term += " " + " ".join(important_words[:2])
        else:
            search_term = " ".join(important_words[:3])
        
        return search_term.strip()
    
    async def search_real_site(self, site_name: str, site_config: dict, search_term: str) -> List[float]:
        """بحث حقيقي في موقع واحد"""
        
        prices = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # رابط البحث
                search_url = site_config['url'].format(search_term.replace(' ', '+'))
                
                print(f"      🔗 {site_config['name']}: {search_url}")
                
                await page.goto(search_url, timeout=site_config['timeout'])
                await page.wait_for_timeout(3000)
                
                # استخراج الأسعار الحقيقية
                real_prices = await page.evaluate(f"""
                    () => {{
                        const prices = new Set();
                        const priceSelectors = {json.dumps(site_config['price_selectors'])};
                        
                        // البحث في عناصر الأسعار المحددة
                        for (const selector of priceSelectors) {{
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(element => {{
                                const text = element.textContent || '';
                                
                                // استخراج الأسعار
                                const priceMatch = text.match(/([0-9,]+(?:\\.[0-9]+)?)/);
                                if (priceMatch) {{
                                    const price = parseFloat(priceMatch[1].replace(/,/g, ''));
                                    if (price >= 20 && price <= 50000) {{
                                        prices.add(price);
                                    }}
                                }}
                            }});
                        }}
                        
                        // البحث في النص الكامل كبديل
                        if (prices.size === 0) {{
                            const bodyText = document.body.innerText || '';
                            const priceMatches = bodyText.match(/([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنيه|EGP)/gi);
                            if (priceMatches) {{
                                priceMatches.forEach(match => {{
                                    const price = parseFloat(match.replace(/[^0-9.]/g, ''));
                                    if (price >= 20 && price <= 50000) {{
                                        prices.add(price);
                                    }}
                                }});
                            }}
                        }}
                        
                        return Array.from(prices).sort((a, b) => a - b).slice(0, 5);
                    }}
                """)
                
                await browser.close()
                
                if real_prices:
                    prices = real_prices
                    print(f"         ✅ وجدت {len(prices)} أسعار حقيقية: {prices}")
                    self.stats['sites_successful'] += 1
                    self.stats['real_prices_found'] += len(prices)
                else:
                    print(f"         ⚪ لم يتم العثور على أسعار")
                
        except Exception as e:
            print(f"         ❌ خطأ: {e}")
        
        self.stats['sites_checked'] += 1
        return prices
    
    async def real_price_comparison(self, product_name: str, amazon_price: float) -> Dict:
        """مقارنة أسعار حقيقية مع المواقع المصرية"""
        
        search_term = self.simplify_product_name(product_name)
        cache_key = f"real_{search_term}_{amazon_price}"
        
        # فحص الكاش
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        print(f"🔍 مقارنة حقيقية: {product_name[:40]}...")
        print(f"   🔎 مصطلح البحث: '{search_term}'")
        
        result = {
            'amazon_price': amazon_price,
            'real_prices': [],
            'sites_data': {},
            'is_good_deal': False,
            'confidence': 0,
            'reason': 'لم يتم العثور على أسعار حقيقية',
            'comparison_type': 'no_comparison',
            'sites_checked': 0,
            'sites_found': 0
        }
        
        all_real_prices = []
        sites_with_prices = []
        
        # البحث في المواقع الحقيقية
        for site_name, site_config in self.real_egyptian_sites.items():
            if not site_config['working']:
                continue
            
            try:
                site_prices = await asyncio.wait_for(
                    self.search_real_site(site_name, site_config, search_term),
                    timeout=12
                )
                
                result['sites_checked'] += 1
                
                if site_prices:
                    all_real_prices.extend(site_prices)
                    sites_with_prices.append(site_config['name'])
                    result['sites_data'][site_name] = {
                        'prices': site_prices,
                        'name': site_config['name']
                    }
                    result['sites_found'] += 1
                
            except asyncio.TimeoutError:
                print(f"      ⏱️ {site_config['name']}: انتهت المهلة")
                result['sites_checked'] += 1
            except Exception as e:
                print(f"      ❌ {site_config['name']}: خطأ")
                result['sites_checked'] += 1
        
        # تحليل النتائج الحقيقية
        if all_real_prices:
            # إزالة التكرار وفلترة
            unique_prices = sorted(list(set(all_real_prices)))
            
            # فلترة الأسعار الغريبة
            if len(unique_prices) > 3:
                median_price = statistics.median(unique_prices)
                filtered_prices = []
                for price in unique_prices:
                    if 0.3 * median_price <= price <= 3 * median_price:
                        filtered_prices.append(price)
                
                if len(filtered_prices) >= 2:
                    unique_prices = filtered_prices
            
            result['real_prices'] = unique_prices
            
            if len(unique_prices) >= 2:
                # تحليل حقيقي
                avg_price = statistics.mean(unique_prices)
                min_price = min(unique_prices)
                max_price = max(unique_prices)
                
                # حساب ترتيب أمازون الحقيقي
                cheaper_count = sum(1 for p in unique_prices if p > amazon_price)
                total_competitors = len(unique_prices)
                amazon_rank = total_competitors - cheaper_count + 1
                
                # حساب الفرق الحقيقي
                vs_avg_diff = ((avg_price - amazon_price) / avg_price) * 100
                
                # تحديد الثقة الحقيقية
                if amazon_rank == 1:
                    result['confidence'] = 85
                    result['reason'] = f"🔥 الأرخص فعلاً من {total_competitors} أسعار حقيقية!"
                    result['is_good_deal'] = True
                elif amazon_rank == 2:
                    result['confidence'] = 75
                    result['reason'] = f"✅ ثاني أرخص من {total_competitors} أسعار حقيقية"
                    result['is_good_deal'] = True
                elif vs_avg_diff > 10:
                    result['confidence'] = 70
                    result['reason'] = f"⚡ أرخص بـ {vs_avg_diff:.0f}% من المتوسط الحقيقي"
                    result['is_good_deal'] = True
                elif amazon_rank <= total_competitors * 0.6:
                    result['confidence'] = 60
                    result['reason'] = f"⚠️ ترتيب {amazon_rank} من {total_competitors} (مقارنة حقيقية)"
                    result['is_good_deal'] = True
                else:
                    result['confidence'] = 45
                    result['reason'] = f"❌ ترتيب {amazon_rank} من {total_competitors} (مقارنة حقيقية)"
                    result['is_good_deal'] = False
                
                result['comparison_type'] = 'real_comparison'
                
                # طباعة النتائج الحقيقية
                print(f"   📊 مقارنة حقيقية:")
                print(f"      💰 متوسط حقيقي: {avg_price:,.0f} EGP")
                print(f"      📉 أقل سعر حقيقي: {min_price:,.0f} EGP")
                print(f"      📈 أعلى سعر حقيقي: {max_price:,.0f} EGP")
                print(f"      🎯 أمازون: {amazon_price:,.0f} EGP (ترتيب {amazon_rank})")
                print(f"      🌐 المواقع: {', '.join(sites_with_prices)}")
                print(f"   {result['reason']}")
                
                self.stats['successful_comparisons'] += 1
            
            else:
                result['confidence'] = 60
                result['reason'] = f"⚪ سعر واحد حقيقي ({unique_prices[0]:.0f}) من {sites_with_prices[0]}"
                result['is_good_deal'] = True
                result['comparison_type'] = 'single_price'
        
        else:
            # لم نجد أسعار حقيقية
            result['confidence'] = 0
            result['reason'] = "❌ لم يتم العثور على أسعار حقيقية للمقارنة"
            result['is_good_deal'] = False
            result['comparison_type'] = 'no_comparison'
        
        self.stats['total_comparisons'] += 1
        
        # حفظ في الكاش
        self.cache[cache_key] = result
        
        return result
    
    def get_real_stats(self) -> Dict:
        """إحصائيات حقيقية للمقارنة"""
        total = self.stats['total_comparisons']
        
        return {
            'total_comparisons': total,
            'successful_comparisons': self.stats['successful_comparisons'],
            'success_rate': (self.stats['successful_comparisons'] / max(total, 1)) * 100,
            'sites_checked': self.stats['sites_checked'],
            'sites_successful': self.stats['sites_successful'],
            'site_success_rate': (self.stats['sites_successful'] / max(self.stats['sites_checked'], 1)) * 100,
            'real_prices_found': self.stats['real_prices_found'],
            'avg_prices_per_comparison': self.stats['real_prices_found'] / max(total, 1),
            'comparison_errors': self.stats['comparison_errors']
        }

# اختبار المقارن الحقيقي
async def test_real_comparator():
    """اختبار المقارن الحقيقي"""
    
    print("🧪 اختبار المقارن الحقيقي")
    print("=" * 50)
    
    comparator = RealPriceComparator()
    
    # منتجات للاختبار
    test_products = [
        {
            'name': 'Samsung Galaxy A06',
            'amazon_price': 2800.0
        },
        {
            'name': 'Vaseline Body Lotion',
            'amazon_price': 85.0
        },
        {
            'name': 'Xiaomi Redmi Note',
            'amazon_price': 3500.0
        }
    ]
    
    successful_tests = 0
    
    for i, product in enumerate(test_products):
        print(f"\n🧪 اختبار {i+1}: {product['name']}")
        
        try:
            result = await comparator.real_price_comparison(
                product['name'], 
                product['amazon_price']
            )
            
            if result['comparison_type'] == 'real_comparison':
                print(f"   ✅ مقارنة حقيقية ناجحة!")
                print(f"      🎯 {result['reason']}")
                successful_tests += 1
            elif result['comparison_type'] == 'single_price':
                print(f"   ⚠️ سعر واحد حقيقي فقط")
                print(f"      🎯 {result['reason']}")
                successful_tests += 0.5
            else:
                print(f"   ❌ لم يتم العثور على أسعار حقيقية")
        
        except Exception as e:
            print(f"   ❌ خطأ في الاختبار: {e}")
        
        print("-" * 40)
    
    # إحصائيات الاختبار
    stats = comparator.get_real_stats()
    print(f"\n📊 إحصائيات الاختبار الحقيقي:")
    print(f"   🧪 اختبارات ناجحة: {successful_tests}/{len(test_products)}")
    print(f"   📈 معدل النجاح: {(successful_tests / len(test_products)) * 100:.1f}%")
    print(f"   🔍 مقارنات حقيقية: {stats['successful_comparisons']}")
    print(f"   🌐 مواقع نجحت: {stats['sites_successful']}/{stats['sites_checked']}")
    print(f"   💰 أسعار حقيقية: {stats['real_prices_found']}")
    
    return successful_tests >= len(test_products) * 0.5

if __name__ == "__main__":
    print("🔍 اختبار نظام المقارنة الحقيقي")
    print("🎯 الهدف: مقارنة حقيقية بدون خداع")
    print()
    
    success = asyncio.run(test_real_comparator())
    
    if success:
        print("\n🎉 النظام الحقيقي يعمل!")
    else:
        print("\n🔧 النظام يحتاج تحسين")
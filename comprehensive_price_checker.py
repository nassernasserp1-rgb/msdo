#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مقارنة الأسعار الشامل مع جميع المواقع المصرية
"""

import asyncio
import requests
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright
import statistics

class ComprehensivePriceChecker:
    """مقارن الأسعار الشامل مع جميع المواقع المصرية"""
    
    def __init__(self):
        # جميع المواقع المصرية الرئيسية
        self.egyptian_sites = {
            'jumia': {
                'name': 'جوميا',
                'search_url': 'https://www.jumia.com.eg/catalog/?q={}',
                'price_selectors': ['.prc', '.-prc', '.price', '.price-now'],
                'product_selectors': ['.core', '.product', '.item'],
                'name_selectors': ['h3', '.name', '.title']
            },
            'noon': {
                'name': 'نون',
                'search_url': 'https://www.noon.com/egypt-en/search?q={}',
                'price_selectors': ['.priceNow', '.price-now', '.price', '.finalPrice'],
                'product_selectors': ['.productContainer', '.product', '.item'],
                'name_selectors': ['h3', '.productTitle', '.title', '.name']
            },
            'souq': {
                'name': 'سوق',
                'search_url': 'https://egypt.souq.com/eg-en/search/?q={}',
                'price_selectors': ['.price', '.price-now', '.current-price'],
                'product_selectors': ['.product', '.item', '.result'],
                'name_selectors': ['h3', '.title', '.name']
            },
            'btech': {
                'name': 'بي تك',
                'search_url': 'https://b-tech.com.eg/search?q={}',
                'price_selectors': ['.price', '.product-price', '.current-price'],
                'product_selectors': ['.product', '.product-item'],
                'name_selectors': ['h3', '.product-title', '.title']
            },
            'tradeline': {
                'name': 'تريد لاين',
                'search_url': 'https://www.tradeline.com.eg/search?q={}',
                'price_selectors': ['.price', '.product-price'],
                'product_selectors': ['.product', '.item'],
                'name_selectors': ['h3', '.title']
            },
            'cairo_sales': {
                'name': 'كايرو سيلز',
                'search_url': 'https://cairosales.com/search?q={}',
                'price_selectors': ['.price', '.current-price'],
                'product_selectors': ['.product'],
                'name_selectors': ['h3', '.title']
            },
            'el_nekhely': {
                'name': 'النخيلي',
                'search_url': 'https://elnekhely.com/search?q={}',
                'price_selectors': ['.price', '.product-price'],
                'product_selectors': ['.product'],
                'name_selectors': ['.title', 'h3']
            }
        }
        
        # إحصائيات المقارنة
        self.comparison_stats = {
            'total_products_checked': 0,
            'successful_comparisons': 0,
            'sites_responses': {site: 0 for site in self.egyptian_sites.keys()},
            'validated_deals': 0,
            'rejected_deals': 0,
            'average_confidence': 0
        }
        
        # كاش للسرعة
        self.price_cache = {}
        
    def clean_product_name(self, product_name: str) -> str:
        """تنظيف اسم المنتج للبحث الأمثل"""
        
        # إزالة الكلمات غير المهمة
        unwanted_words = [
            'amazon', 'choice', 'brand', 'pack', 'piece', 'set', 'kit',
            'أمازون', 'قطعة', 'حبة', 'عبوة', 'مجموعة', 'طقم'
        ]
        
        # تنظيف النص
        clean_name = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', product_name.lower())
        clean_name = re.sub(r'\d+\s*(piece|pack|ml|kg|gram|لتر|كيلو|قطعة)', '', clean_name)
        
        # فلترة الكلمات
        words = clean_name.split()
        important_words = []
        
        for word in words:
            if (len(word) > 2 and 
                word not in unwanted_words and 
                not word.isdigit()):
                important_words.append(word)
        
        # أخذ أهم 4 كلمات للبحث الدقيق
        search_terms = ' '.join(important_words[:4])
        
        return search_terms.strip()
    
    def calculate_name_similarity(self, amazon_name: str, external_name: str) -> float:
        """حساب مدى تشابه أسماء المنتجات"""
        
        amazon_words = set(self.clean_product_name(amazon_name).split())
        external_words = set(self.clean_product_name(external_name).split())
        
        if not amazon_words or not external_words:
            return 0.0
        
        # الكلمات المشتركة
        common_words = amazon_words & external_words
        total_words = amazon_words | external_words
        
        if not total_words:
            return 0.0
        
        # نسبة التشابه الأساسية
        basic_similarity = len(common_words) / len(total_words)
        
        # إضافة نقاط للعلامات التجارية المهمة
        important_brands = [
            'iphone', 'samsung', 'sony', 'lg', 'xiaomi', 'huawei', 'apple',
            'nike', 'adidas', 'canon', 'nikon', 'hp', 'dell', 'lenovo'
        ]
        
        brand_bonus = 0
        for brand in important_brands:
            if brand in amazon_name.lower() and brand in external_name.lower():
                brand_bonus += 0.3
        
        # إضافة نقاط للأرقام المطابقة (موديلات)
        amazon_numbers = set(re.findall(r'\d+', amazon_name))
        external_numbers = set(re.findall(r'\d+', external_name))
        number_bonus = len(amazon_numbers & external_numbers) * 0.1
        
        final_similarity = min(1.0, basic_similarity + brand_bonus + number_bonus)
        
        return final_similarity
    
    async def search_in_site(self, site_key: str, search_term: str) -> List[Dict]:
        """البحث في موقع محدد"""
        
        site_info = self.egyptian_sites[site_key]
        search_url = site_info['search_url'].format(search_term.replace(' ', '+'))
        
        products_found = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-images',
                        '--disable-css',
                        '--disable-javascript',
                        '--window-size=1280,720'
                    ]
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                # الذهاب للموقع
                await page.goto(search_url, timeout=12000)
                await page.wait_for_timeout(2000)
                
                # استخراج المنتجات والأسعار
                products_data = await page.evaluate(f"""
                    () => {{
                        const products = [];
                        const productSelectors = {json.dumps(site_info['product_selectors'])};
                        const priceSelectors = {json.dumps(site_info['price_selectors'])};
                        const nameSelectors = {json.dumps(site_info['name_selectors'])};
                        
                        // البحث عن عناصر المنتجات
                        let productElements = [];
                        for (const selector of productSelectors) {{
                            const elements = document.querySelectorAll(selector);
                            if (elements.length > 0) {{
                                productElements = Array.from(elements).slice(0, 5); // أول 5 منتجات فقط
                                break;
                            }}
                        }}
                        
                        productElements.forEach(element => {{
                            // البحث عن اسم المنتج
                            let productName = '';
                            for (const selector of nameSelectors) {{
                                const nameEl = element.querySelector(selector);
                                if (nameEl && nameEl.textContent.trim()) {{
                                    productName = nameEl.textContent.trim();
                                    break;
                                }}
                            }}
                            
                            // البحث عن السعر
                            let price = null;
                            for (const selector of priceSelectors) {{
                                const priceEl = element.querySelector(selector);
                                if (priceEl) {{
                                    const priceText = priceEl.textContent;
                                    const match = priceText.match(/([0-9,]+)/);
                                    if (match) {{
                                        const extractedPrice = parseFloat(match[1].replace(/,/g, ''));
                                        if (extractedPrice > 10 && extractedPrice < 200000) {{
                                            price = extractedPrice;
                                            break;
                                        }}
                                    }}
                                }}
                            }}
                            
                            // البحث عن الرابط
                            const linkEl = element.querySelector('a[href]');
                            const productUrl = linkEl ? linkEl.href : '';
                            
                            if (productName && price) {{
                                products.push({{
                                    name: productName,
                                    price: price,
                                    url: productUrl,
                                    site: '{site_key}'
                                }});
                            }}
                        }});
                        
                        return products;
                    }}
                """)
                
                products_found = products_data
                self.comparison_stats['sites_responses'][site_key] += len(products_found)
                
                await browser.close()
                
                if products_found:
                    print(f"   ✅ {site_info['name']}: وُجد {len(products_found)} منتج")
                else:
                    print(f"   ⚪ {site_info['name']}: لا توجد نتائج")
                
        except Exception as e:
            print(f"   ❌ {site_info['name']}: خطأ في البحث ({str(e)[:50]})")
        
        return products_found
    
    async def comprehensive_price_comparison(self, amazon_product: Dict, amazon_price: float) -> Dict:
        """مقارنة شاملة مع جميع المواقع المصرية"""
        
        product_name = amazon_product.get('name', '')
        search_term = self.clean_product_name(product_name)
        
        print(f"🔍 مقارنة شاملة: {product_name[:50]}...")
        print(f"   🔎 البحث عن: '{search_term}'")
        
        # البحث في جميع المواقع بالتوازي
        search_tasks = []
        for site_key in self.egyptian_sites.keys():
            task = self.search_in_site(site_key, search_term)
            search_tasks.append((site_key, task))
        
        all_external_products = []
        sites_with_results = []
        
        # تجميع النتائج من جميع المواقع
        for site_key, task in search_tasks:
            try:
                products = await task
                if products:
                    # العثور على أفضل مطابقة
                    best_match = self.find_best_match(amazon_product, products)
                    if best_match and best_match['similarity'] > 0.3:  # حد أدنى للتشابه
                        all_external_products.append({
                            'site': site_key,
                            'site_name': self.egyptian_sites[site_key]['name'],
                            'price': best_match['price'],
                            'name': best_match['name'],
                            'similarity': best_match['similarity'],
                            'url': best_match.get('url', '')
                        })
                        sites_with_results.append(site_key)
            except Exception as e:
                print(f"   ❌ خطأ في معالجة نتائج {site_key}: {e}")
        
        # تحليل النتائج
        comparison_result = {
            'amazon_price': amazon_price,
            'external_products': all_external_products,
            'sites_checked': len(self.egyptian_sites),
            'sites_with_results': len(sites_with_results),
            'is_good_deal': False,
            'confidence_score': 0,
            'detailed_analysis': {},
            'recommendation': 'unknown'
        }
        
        if all_external_products:
            # حساب الإحصائيات
            external_prices = [p['price'] for p in all_external_products]
            avg_market_price = statistics.mean(external_prices)
            min_market_price = min(external_prices)
            max_market_price = max(external_prices)
            median_market_price = statistics.median(external_prices)
            
            # حساب الفروق
            vs_avg_diff = ((avg_market_price - amazon_price) / avg_market_price) * 100
            vs_min_diff = ((min_market_price - amazon_price) / min_market_price) * 100
            vs_median_diff = ((median_market_price - amazon_price) / median_market_price) * 100
            
            comparison_result['detailed_analysis'] = {
                'avg_market_price': avg_market_price,
                'min_market_price': min_market_price,
                'max_market_price': max_market_price,
                'median_market_price': median_market_price,
                'vs_avg_difference': vs_avg_diff,
                'vs_min_difference': vs_min_diff,
                'vs_median_difference': vs_median_diff,
                'price_range': max_market_price - min_market_price,
                'market_consistency': self.calculate_market_consistency(external_prices)
            }
            
            # تحديد جودة العرض بناءً على مقارنة شاملة
            confidence_factors = []
            
            # عامل 1: مقارنة مع المتوسط
            if vs_avg_diff > 20:
                confidence_factors.append(('متوسط السوق', 30, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
            elif vs_avg_diff > 10:
                confidence_factors.append(('متوسط السوق', 20, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
            elif vs_avg_diff > 0:
                confidence_factors.append(('متوسط السوق', 10, f"أرخص بـ {vs_avg_diff:.0f}% من المتوسط"))
            else:
                confidence_factors.append(('متوسط السوق', -20, f"أغلى بـ {abs(vs_avg_diff):.0f}% من المتوسط"))
            
            # عامل 2: مقارنة مع أقل سعر
            if vs_min_diff > 5:
                confidence_factors.append(('أقل سعر', 25, f"أرخص بـ {vs_min_diff:.0f}% من أقل سعر"))
            elif vs_min_diff > -5:
                confidence_factors.append(('أقل سعر', 15, f"مقارب لأقل سعر ({vs_min_diff:+.0f}%)"))
            else:
                confidence_factors.append(('أقل سعر', -15, f"أغلى بـ {abs(vs_min_diff):.0f}% من أقل سعر"))
            
            # عامل 3: عدد المواقع التي وُجد فيها
            sites_bonus = len(sites_with_results) * 5
            confidence_factors.append(('تواجد في السوق', sites_bonus, f"موجود في {len(sites_with_results)} مواقع"))
            
            # عامل 4: ثبات السوق
            market_consistency = comparison_result['detailed_analysis']['market_consistency']
            if market_consistency > 0.8:
                confidence_factors.append(('ثبات السوق', 15, 'أسعار السوق متسقة'))
            elif market_consistency > 0.6:
                confidence_factors.append(('ثبات السوق', 5, 'أسعار السوق متوسطة الثبات'))
            else:
                confidence_factors.append(('ثبات السوق', -10, 'أسعار السوق متذبذبة'))
            
            # حساب النقاط النهائية
            total_confidence = 50  # نقطة البداية
            for factor_name, points, description in confidence_factors:
                total_confidence += points
            
            comparison_result['confidence_score'] = max(0, min(100, total_confidence))
            comparison_result['confidence_factors'] = confidence_factors
            
            # تحديد التوصية النهائية
            if comparison_result['confidence_score'] >= 75:
                comparison_result['is_good_deal'] = True
                comparison_result['recommendation'] = f"🔥 عرض ممتاز! مؤكد من {len(sites_with_results)} مواقع"
                
            elif comparison_result['confidence_score'] >= 60:
                comparison_result['is_good_deal'] = True
                comparison_result['recommendation'] = f"✅ عرض جيد! مقارنة مع {len(sites_with_results)} مواقع"
                
            elif comparison_result['confidence_score'] >= 45:
                comparison_result['is_good_deal'] = True
                comparison_result['recommendation'] = f"⚠️ عرض مقبول! فحص {len(sites_with_results)} مواقع"
                
            else:
                comparison_result['is_good_deal'] = False
                comparison_result['recommendation'] = f"❌ عرض مرفوض! أغلى من {len(sites_with_results)} مواقع"
            
            # طباعة التفاصيل
            print(f"   📊 تحليل شامل:")
            print(f"      💰 متوسط السوق: {avg_market_price:,.0f} EGP")
            print(f"      📉 أقل سعر: {min_market_price:,.0f} EGP")
            print(f"      📈 أعلى سعر: {max_market_price:,.0f} EGP")
            print(f"      🎯 أمازون: {amazon_price:,.0f} EGP")
            print(f"      📊 الفرق عن المتوسط: {vs_avg_diff:+.1f}%")
            print(f"      🏆 الثقة: {comparison_result['confidence_score']}/100")
            print(f"   {comparison_result['recommendation']}")
            
            self.comparison_stats['successful_comparisons'] += 1
        else:
            comparison_result['recommendation'] = "⚠️ لم يتم العثور على منتجات مطابقة للمقارنة"
            comparison_result['confidence_score'] = 30
            print(f"   ⚠️ لم يتم العثور على منتجات مطابقة في أي موقع")
        
        self.comparison_stats['total_products_checked'] += 1
        
        return comparison_result
    
    def find_best_match(self, amazon_product: Dict, external_products: List[Dict]) -> Optional[Dict]:
        """العثور على أفضل منتج مطابق"""
        
        amazon_name = amazon_product.get('name', '')
        amazon_price = amazon_product.get('price', 0)
        
        best_match = None
        best_score = 0
        
        for product in external_products:
            # حساب التشابه في الاسم
            name_similarity = self.calculate_name_similarity(amazon_name, product['name'])
            
            # حساب التشابه في السعر (المنتجات المشابهة لها أسعار متقاربة نسبياً)
            price_similarity = 0
            if amazon_price > 0 and product['price'] > 0:
                price_ratio = min(amazon_price, product['price']) / max(amazon_price, product['price'])
                if price_ratio > 0.3:  # إذا كان الفرق أقل من 70%
                    price_similarity = price_ratio * 0.2
            
            total_score = name_similarity + price_similarity
            
            if total_score > best_score and name_similarity > 0.4:
                best_score = total_score
                best_match = product.copy()
                best_match['similarity'] = name_similarity
                best_match['total_score'] = total_score
        
        return best_match
    
    def calculate_market_consistency(self, prices: List[float]) -> float:
        """حساب ثبات أسعار السوق"""
        if len(prices) < 2:
            return 0.5
        
        try:
            avg_price = statistics.mean(prices)
            std_dev = statistics.stdev(prices)
            
            # معامل التباين
            coefficient_of_variation = std_dev / avg_price if avg_price > 0 else 1
            
            # كلما قل التباين، كلما زاد الثبات
            consistency = max(0, 1 - coefficient_of_variation)
            
            return consistency
            
        except Exception:
            return 0.5
    
    def get_comprehensive_stats(self) -> Dict:
        """الحصول على إحصائيات شاملة"""
        total_checked = self.comparison_stats['total_products_checked']
        
        return {
            'total_products_checked': total_checked,
            'successful_comparisons': self.comparison_stats['successful_comparisons'],
            'success_rate': (self.comparison_stats['successful_comparisons'] / max(total_checked, 1)) * 100,
            'validated_deals': self.comparison_stats['validated_deals'],
            'rejected_deals': self.comparison_stats['rejected_deals'],
            'validation_rate': (self.comparison_stats['validated_deals'] / max(total_checked, 1)) * 100,
            'sites_responses': self.comparison_stats['sites_responses'],
            'total_sites': len(self.egyptian_sites)
        }

# إنشاء مقارن الأسعار الشامل
comprehensive_checker = ComprehensivePriceChecker()

async def validate_deal_with_comprehensive_comparison(item: Dict, old_price: float, 
                                                    new_price: float, discount_percent: float) -> Tuple[bool, str]:
    """التحقق من العرض عن طريق المقارنة الشاملة"""
    
    try:
        comparison_result = await comprehensive_checker.comprehensive_price_comparison(item, new_price)
        
        should_send = comparison_result['is_good_deal']
        reason = comparison_result['recommendation']
        confidence = comparison_result['confidence_score']
        
        # إضافة معلومات المقارنة للمنتج
        item['comprehensive_comparison'] = comparison_result
        item['market_confidence'] = confidence
        item['market_recommendation'] = reason
        
        if should_send:
            comprehensive_checker.comparison_stats['validated_deals'] += 1
            return True, f"{reason} (ثقة: {confidence}%)"
        else:
            comprehensive_checker.comparison_stats['rejected_deals'] += 1
            return False, f"{reason} (ثقة: {confidence}%)"
    
    except Exception as e:
        print(f"❌ خطأ في المقارنة الشاملة: {e}")
        # في حالة الخطأ، استخدم فلترة أساسية
        if discount_percent <= 75 and new_price >= 30:
            return True, "⚠️ مقارنة خارجية فشلت - فلترة أساسية"
        else:
            return False, "❌ مقارنة خارجية فشلت + عرض مشبوه"

# اختبار النظام
async def test_comprehensive_comparison():
    """اختبار النظام الشامل"""
    
    print("🧪 اختبار نظام المقارنة الشامل")
    print("=" * 60)
    
    test_products = [
        {
            'name': 'iPhone 15 Pro Max 256GB Natural Titanium',
            'price': 42000,
            'section': 'Electronics',
            'asin': 'B0CHX1W1XY'
        },
        {
            'name': 'Samsung Galaxy Buds2 Pro Wireless Earbuds',
            'price': 3200,
            'section': 'Electronics',
            'asin': 'B0B2SH4MQS'
        },
        {
            'name': 'Nike Air Force 1 White Sneakers',
            'price': 2800,
            'section': 'Fashion',
            'asin': 'B08XYZ123'
        }
    ]
    
    for product in test_products:
        print(f"\n🧪 اختبار: {product['name']}")
        
        # محاكاة خصم
        old_price = product['price'] * 1.25
        new_price = product['price']
        discount = ((old_price - new_price) / old_price) * 100
        
        print(f"   💰 السعر: {old_price:,.0f} → {new_price:,.0f} ({discount:.1f}% OFF)")
        
        should_send, reason = await validate_deal_with_comprehensive_comparison(
            product, old_price, new_price, discount
        )
        
        if should_send:
            print(f"   ✅ {reason}")
        else:
            print(f"   ❌ {reason}")
        
        print("-" * 40)
    
    # طباعة الإحصائيات النهائية
    stats = comprehensive_checker.get_comprehensive_stats()
    print(f"\n📊 إحصائيات الاختبار:")
    print(f"   🔍 منتجات مفحوصة: {stats['total_products_checked']}")
    print(f"   ✅ مقارنات ناجحة: {stats['successful_comparisons']}")
    print(f"   📱 عروض معتمدة: {stats['validated_deals']}")
    print(f"   🚫 عروض مرفوضة: {stats['rejected_deals']}")
    print(f"   📈 معدل النجاح: {stats['success_rate']:.1f}%")
    print(f"   🎯 معدل الاعتماد: {stats['validation_rate']:.1f}%")
    
    print(f"\n🌐 استجابة المواقع:")
    for site, count in stats['sites_responses'].items():
        site_name = comprehensive_checker.egyptian_sites[site]['name']
        print(f"   {site_name}: {count} منتج")

if __name__ == "__main__":
    print("🔍 نظام المقارنة الشامل مع جميع المواقع المصرية")
    print("🌐 المواقع المشمولة: جوميا، نون، سوق، بي تك، تريد لاين، كايرو سيلز، النخيلي")
    print()
    
    asyncio.run(test_comprehensive_comparison())
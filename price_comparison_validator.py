#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مقارنة الأسعار مع المواقع الخارجية للتحقق من العروض الحقيقية
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

class PriceComparisonValidator:
    """مُحقق العروض عن طريق مقارنة الأسعار مع مواقع أخرى"""
    
    def __init__(self):
        # مواقع المقارنة
        self.comparison_sites = {
            'jumia': {
                'search_url': 'https://www.jumia.com.eg/catalog/?q={}',
                'price_selector': '.prc, .-prc, .price',
                'name': 'Jumia'
            },
            'noon': {
                'search_url': 'https://www.noon.com/egypt-en/search?q={}',
                'price_selector': '.priceNow, .price-now, .price',
                'name': 'Noon'
            },
            'souq': {
                'search_url': 'https://egypt.souq.com/eg-en/search/?q={}',
                'price_selector': '.price, .price-now, .current-price',
                'name': 'Souq'
            },
            'b_tech': {
                'search_url': 'https://b-tech.com.eg/search?q={}',
                'price_selector': '.price, .product-price, .current-price',
                'name': 'B.Tech'
            }
        }
        
        # إعدادات المقارنة
        self.comparison_settings = {
            'max_price_difference': 30,  # أقصى فرق سعر مقبول (%)
            'min_sites_to_compare': 2,   # أقل عدد مواقع للمقارنة
            'search_timeout': 15,        # مهلة البحث لكل موقع
            'price_tolerance': 20        # هامش تسامح في السعر (%)
        }
        
        # نتائج المقارنة
        self.comparison_results = []
        self.validated_deals = []
        self.rejected_deals = []
        
    def clean_product_name_for_search(self, product_name: str) -> str:
        """تنظيف اسم المنتج للبحث"""
        
        # إزالة الكلمات غير المهمة
        unwanted_words = [
            'amazon', 'choice', 'brand', 'pack', 'piece', 'set',
            'أمازون', 'قطعة', 'حبة', 'عبوة', 'مجموعة'
        ]
        
        # تنظيف الاسم
        clean_name = product_name.lower()
        
        # إزالة الأرقام والرموز الزائدة
        clean_name = re.sub(r'\d+\s*(piece|pack|ml|kg|gram|لتر|كيلو)', '', clean_name)
        clean_name = re.sub(r'[^\w\s]', ' ', clean_name)
        
        # إزالة الكلمات غير المهمة
        words = clean_name.split()
        filtered_words = [word for word in words if word not in unwanted_words and len(word) > 2]
        
        # أخذ أهم 3-4 كلمات
        search_terms = ' '.join(filtered_words[:4])
        
        return search_terms.strip()
    
    async def search_product_on_site(self, site_key: str, product_name: str) -> List[Dict]:
        """البحث عن المنتج في موقع محدد"""
        
        site_info = self.comparison_sites[site_key]
        search_query = self.clean_product_name_for_search(product_name)
        search_url = site_info['search_url'].format(search_query)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-images', '--disable-javascript']
                )
                context = await browser.new_context()
                page = await context.new_page()
                
                # الذهاب لصفحة البحث
                await page.goto(search_url, timeout=self.comparison_settings['search_timeout'] * 1000)
                await page.wait_for_timeout(3000)
                
                # استخراج المنتجات والأسعار
                products_data = await page.evaluate(f"""
                    () => {{
                        const products = [];
                        const productElements = document.querySelectorAll('.product, .product-item, .item, [data-qa="product"]');
                        
                        productElements.forEach((element, index) => {{
                            if (index >= 10) return; // أول 10 منتجات فقط
                            
                            // البحث عن اسم المنتج
                            const nameSelectors = ['h3', '.title', '.product-title', '.name', 'h2', 'h4'];
                            let productName = '';
                            for (const selector of nameSelectors) {{
                                const nameEl = element.querySelector(selector);
                                if (nameEl && nameEl.textContent.trim()) {{
                                    productName = nameEl.textContent.trim();
                                    break;
                                }}
                            }}
                            
                            // البحث عن السعر
                            const priceSelectors = ['{site_info['price_selector']}', '.price-current', '.price-final', '.current'];
                            let price = null;
                            for (const selector of priceSelectors) {{
                                const priceEl = element.querySelector(selector);
                                if (priceEl) {{
                                    const priceText = priceEl.textContent;
                                    const match = priceText.match(/([0-9,]+)/);
                                    if (match) {{
                                        price = parseFloat(match[1].replace(/,/g, ''));
                                        break;
                                    }}
                                }}
                            }}
                            
                            // البحث عن الرابط
                            const linkEl = element.querySelector('a[href]');
                            const productUrl = linkEl ? linkEl.href : '';
                            
                            if (productName && price && price > 10) {{
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
                
                await browser.close()
                return products_data
                
        except Exception as e:
            print(f"⚠️ خطأ في البحث في {site_info['name']}: {e}")
            return []
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """حساب مدى تشابه أسماء المنتجات"""
        
        # تنظيف الأسماء
        clean1 = re.sub(r'[^\w\s]', '', name1.lower()).split()
        clean2 = re.sub(r'[^\w\s]', '', name2.lower()).split()
        
        # حساب الكلمات المشتركة
        common_words = set(clean1) & set(clean2)
        total_words = set(clean1) | set(clean2)
        
        if not total_words:
            return 0.0
        
        # نسبة التشابه
        similarity = len(common_words) / len(total_words)
        
        # إضافة نقاط إضافية للكلمات المهمة
        important_words = ['iphone', 'samsung', 'sony', 'lg', 'xiaomi', 'huawei', 'apple']
        for word in important_words:
            if word in name1.lower() and word in name2.lower():
                similarity += 0.2
        
        return min(1.0, similarity)
    
    def find_best_match(self, amazon_product: Dict, external_products: List[Dict]) -> Optional[Dict]:
        """العثور على أفضل منتج مطابق في المواقع الخارجية"""
        
        amazon_name = amazon_product.get('name', '')
        amazon_price = amazon_product.get('price', 0)
        
        best_match = None
        best_similarity = 0
        
        for product in external_products:
            # حساب التشابه في الاسم
            similarity = self.calculate_name_similarity(amazon_name, product['name'])
            
            # حساب التشابه في السعر (المنتجات المشابهة لها أسعار متقاربة)
            price_similarity = 0
            if amazon_price > 0 and product['price'] > 0:
                price_ratio = min(amazon_price, product['price']) / max(amazon_price, product['price'])
                price_similarity = price_ratio * 0.3  # وزن أقل للسعر
            
            total_similarity = similarity + price_similarity
            
            if total_similarity > best_similarity and similarity > 0.4:  # حد أدنى للتشابه
                best_similarity = total_similarity
                best_match = product
                best_match['similarity_score'] = similarity
                best_match['total_similarity'] = total_similarity
        
        return best_match
    
    async def compare_prices_across_sites(self, amazon_product: Dict) -> Dict:
        """مقارنة أسعار المنتج عبر جميع المواقع"""
        
        product_name = amazon_product.get('name', '')
        amazon_price = amazon_product.get('price', 0)
        
        print(f"🔍 مقارنة أسعار: {product_name[:50]}...")
        
        comparison_result = {
            'amazon_price': amazon_price,
            'external_prices': {},
            'best_matches': {},
            'price_analysis': {},
            'is_good_deal': False,
            'confidence_score': 0,
            'comparison_summary': ''
        }
        
        # البحث في جميع المواقع بالتوازي
        search_tasks = []
        for site_key in self.comparison_sites.keys():
            task = self.search_product_on_site(site_key, product_name)
            search_tasks.append((site_key, task))
        
        # تجميع النتائج
        external_matches = {}
        for site_key, task in search_tasks:
            try:
                products = await task
                if products:
                    best_match = self.find_best_match(amazon_product, products)
                    if best_match:
                        external_matches[site_key] = best_match
                        comparison_result['external_prices'][site_key] = best_match['price']
                        comparison_result['best_matches'][site_key] = best_match
                        
                        print(f"   ✅ {self.comparison_sites[site_key]['name']}: {best_match['price']:,.0f} EGP (تشابه: {best_match['similarity_score']:.0%})")
                    else:
                        print(f"   ⚪ {self.comparison_sites[site_key]['name']}: لم يتم العثور على منتج مطابق")
                else:
                    print(f"   ❌ {self.comparison_sites[site_key]['name']}: لا توجد نتائج")
            except Exception as e:
                print(f"   ❌ {self.comparison_sites[site_key]['name']}: خطأ في البحث")
        
        # تحليل النتائج
        if external_matches:
            external_prices = [match['price'] for match in external_matches.values()]
            avg_external_price = statistics.mean(external_prices)
            min_external_price = min(external_prices)
            max_external_price = max(external_prices)
            
            # حساب الفروق
            vs_avg_diff = ((avg_external_price - amazon_price) / avg_external_price) * 100
            vs_min_diff = ((min_external_price - amazon_price) / min_external_price) * 100
            
            comparison_result['price_analysis'] = {
                'avg_external_price': avg_external_price,
                'min_external_price': min_external_price,
                'max_external_price': max_external_price,
                'vs_avg_difference': vs_avg_diff,
                'vs_min_difference': vs_min_diff,
                'sites_found': len(external_matches)
            }
            
            # تحديد جودة العرض
            if vs_avg_diff > 20:  # أمازون أرخص بأكثر من 20% من المتوسط
                comparison_result['is_good_deal'] = True
                comparison_result['confidence_score'] = 90
                comparison_result['comparison_summary'] = f"🔥 عرض ممتاز! أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                
            elif vs_avg_diff > 10:  # أرخص بأكثر من 10%
                comparison_result['is_good_deal'] = True
                comparison_result['confidence_score'] = 75
                comparison_result['comparison_summary'] = f"✅ عرض جيد! أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                
            elif vs_avg_diff > 0:  # أرخص قليلاً
                comparison_result['is_good_deal'] = True
                comparison_result['confidence_score'] = 60
                comparison_result['comparison_summary'] = f"⚠️ عرض مقبول! أرخص بـ {vs_avg_diff:.0f}% من المتوسط"
                
            elif vs_avg_diff > -15:  # أغلى قليلاً (مقبول)
                comparison_result['is_good_deal'] = False
                comparison_result['confidence_score'] = 40
                comparison_result['comparison_summary'] = f"🤔 سعر مرتفع قليلاً بـ {abs(vs_avg_diff):.0f}% من المتوسط"
                
            else:  # أغلى بكثير
                comparison_result['is_good_deal'] = False
                comparison_result['confidence_score'] = 20
                comparison_result['comparison_summary'] = f"❌ سعر مرتفع! أغلى بـ {abs(vs_avg_diff):.0f}% من المتوسط"
            
            print(f"   📊 المقارنة: أمازون {amazon_price:,.0f} vs متوسط السوق {avg_external_price:,.0f}")
            print(f"   {comparison_result['comparison_summary']}")
            
        else:
            # لم يتم العثور على منتجات مطابقة
            comparison_result['confidence_score'] = 30
            comparison_result['comparison_summary'] = "⚠️ لم يتم العثور على منتجات مطابقة للمقارنة"
            print(f"   ⚠️ لم يتم العثور على منتجات مطابقة في المواقع الأخرى")
        
        return comparison_result
    
    async def validate_deal_with_external_comparison(self, amazon_product: Dict, 
                                                   old_price: float, new_price: float, 
                                                   discount_percent: float) -> Tuple[bool, str, Dict]:
        """التحقق من العرض عن طريق مقارنة خارجية"""
        
        print(f"\n🔍 بدء مقارنة خارجية للمنتج: {amazon_product.get('name', '')[:50]}...")
        
        # تحديث سعر المنتج للمقارنة
        amazon_product_for_comparison = amazon_product.copy()
        amazon_product_for_comparison['price'] = new_price
        
        # مقارنة الأسعار
        comparison_result = await self.compare_prices_across_sites(amazon_product_for_comparison)
        
        # حفظ النتيجة
        comparison_record = {
            'amazon_product': amazon_product,
            'old_price': old_price,
            'new_price': new_price,
            'discount_percent': discount_percent,
            'comparison_result': comparison_result,
            'timestamp': datetime.now().isoformat()
        }
        
        self.comparison_results.append(comparison_record)
        
        # تحديد القرار
        should_send = comparison_result['is_good_deal']
        confidence = comparison_result['confidence_score']
        summary = comparison_result['comparison_summary']
        
        if should_send:
            self.validated_deals.append(comparison_record)
            return True, f"✅ {summary} (ثقة: {confidence}%)", comparison_result
        else:
            self.rejected_deals.append(comparison_record)
            return False, f"❌ {summary} (ثقة: {confidence}%)", comparison_result
    
    def get_comparison_stats(self) -> Dict:
        """الحصول على إحصائيات المقارنة"""
        total_comparisons = len(self.comparison_results)
        validated = len(self.validated_deals)
        rejected = len(self.rejected_deals)
        
        if total_comparisons > 0:
            success_rate = (validated / total_comparisons) * 100
            avg_confidence = statistics.mean([r['comparison_result']['confidence_score'] for r in self.comparison_results])
        else:
            success_rate = 0
            avg_confidence = 0
        
        return {
            'total_comparisons': total_comparisons,
            'validated_deals': validated,
            'rejected_deals': rejected,
            'success_rate': success_rate,
            'avg_confidence': avg_confidence,
            'sites_used': list(self.comparison_sites.keys())
        }
    
    def generate_comparison_report(self) -> str:
        """إنشاء تقرير المقارنة"""
        stats = self.get_comparison_stats()
        
        report = f"""
🔍 تقرير مقارنة الأسعار الخارجية:
=====================================

📊 إحصائيات عامة:
- إجمالي المقارنات: {stats['total_comparisons']}
- العروض المعتمدة: {stats['validated_deals']}
- العروض المرفوضة: {stats['rejected_deals']}
- معدل النجاح: {stats['success_rate']:.1f}%
- متوسط الثقة: {stats['avg_confidence']:.1f}%

🌐 المواقع المستخدمة: {', '.join([self.comparison_sites[site]['name'] for site in stats['sites_used']])}

🏆 أفضل 5 عروض معتمدة:
"""
        
        # أفضل العروض
        top_deals = sorted(
            self.validated_deals,
            key=lambda x: x['comparison_result']['confidence_score'],
            reverse=True
        )[:5]
        
        for i, deal in enumerate(top_deals, 1):
            name = deal['amazon_product']['name'][:40]
            price = deal['new_price']
            confidence = deal['comparison_result']['confidence_score']
            summary = deal['comparison_result']['comparison_summary']
            
            report += f"\n{i}. {name}... - {price:,.0f} EGP ({confidence}% ثقة)"
            report += f"\n   {summary}"
        
        return report

# دالة للتكامل مع السكرابر
price_validator = PriceComparisonValidator()

async def validate_deal_with_price_comparison(item, old_price, new_price, discount_percent):
    """التحقق من العرض عن طريق مقارنة الأسعار"""
    
    try:
        should_send, reason, comparison_data = await price_validator.validate_deal_with_external_comparison(
            item, old_price, new_price, discount_percent
        )
        
        # إضافة معلومات المقارنة للمنتج
        item['price_comparison'] = comparison_data
        item['comparison_reason'] = reason
        
        return should_send, reason
        
    except Exception as e:
        print(f"❌ خطأ في مقارنة الأسعار: {e}")
        # في حالة الخطأ، اعتمد على التحقق الأساسي
        if discount_percent <= 70 and new_price >= 50:
            return True, "⚠️ مقارنة خارجية فشلت - اعتماد على التحقق الأساسي"
        else:
            return False, "❌ مقارنة خارجية فشلت + عرض مشبوه"

# اختبار النظام
async def test_price_comparison():
    """اختبار نظام مقارنة الأسعار"""
    
    print("🧪 اختبار نظام مقارنة الأسعار")
    print("=" * 50)
    
    # منتجات اختبار
    test_products = [
        {
            'name': 'iPhone 15 Pro Max 256GB',
            'price': 45000,
            'section': 'Electronics',
            'asin': 'B0CHX1W1XY'
        },
        {
            'name': 'Samsung Galaxy S24 Ultra',
            'price': 38000,
            'section': 'Electronics', 
            'asin': 'B0CMDRCGZX'
        },
        {
            'name': 'Sony WH-1000XM5 Headphones',
            'price': 8500,
            'section': 'Electronics',
            'asin': 'B09XS7JWHH'
        }
    ]
    
    for product in test_products:
        print(f"\n🧪 اختبار: {product['name']}")
        
        # محاكاة خصم
        old_price = product['price'] * 1.3  # سعر أصلي أعلى بـ 30%
        new_price = product['price']
        discount = ((old_price - new_price) / old_price) * 100
        
        print(f"   💰 السعر: {old_price:,.0f} → {new_price:,.0f} ({discount:.1f}% OFF)")
        
        should_send, reason = await validate_deal_with_price_comparison(
            product, old_price, new_price, discount
        )
        
        if should_send:
            print(f"   ✅ {reason}")
        else:
            print(f"   ❌ {reason}")
    
    # طباعة التقرير
    print(price_validator.generate_comparison_report())

if __name__ == "__main__":
    asyncio.run(test_price_comparison())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار البحث الحقيقي في جوجل
لمعرفة الطريقة الصحيحة للحصول على أسعار حقيقية
"""

import asyncio
import re
from playwright.async_api import async_playwright

async def test_real_google_search():
    """اختبار البحث الحقيقي في جوجل بطرق مختلفة"""
    
    print("🔍 اختبار البحث الحقيقي في جوجل")
    print("=" * 60)
    
    # منتج للاختبار (من النتائج اللي شفناها)
    test_product = "Care & More Soft Cream With Glycerin Tropical 75 ML"
    amazon_price = 30.0
    
    print(f"🧪 منتج الاختبار: {test_product}")
    print(f"💰 سعر أمازون: {amazon_price} EGP")
    print()
    
    # طرق بحث مختلفة للاختبار
    search_methods = [
        {
            'name': 'البحث العادي',
            'url': 'https://www.google.com/search?q=care+more+soft+cream+glycerin+سعر&hl=ar&gl=EG',
            'description': 'بحث عادي في جوجل'
        },
        {
            'name': 'جوجل شوبينج',
            'url': 'https://www.google.com/search?q=care+more+soft+cream&tbm=shop&hl=ar&gl=EG',
            'description': 'البحث في جوجل شوبينج'
        },
        {
            'name': 'البحث بالعربية',
            'url': 'https://www.google.com/search?q=كير+اند+مور+كريم+سعر+مصر&hl=ar&gl=EG',
            'description': 'بحث بالعربية'
        },
        {
            'name': 'البحث المباشر',
            'url': 'https://www.google.com/search?q="care+more+soft+cream"+price+egypt&hl=en&gl=EG',
            'description': 'بحث مباشر بالإنجليزية'
        }
    ]
    
    successful_methods = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # نشوف الصفحة بصرياً
            args=['--no-sandbox', '--window-size=1920,1080']
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        for i, method in enumerate(search_methods):
            print(f"\n🧪 اختبار {i+1}: {method['name']}")
            print(f"   📝 الوصف: {method['description']}")
            print(f"   🔗 الرابط: {method['url']}")
            
            try:
                await page.goto(method['url'], timeout=15000)
                await page.wait_for_timeout(5000)  # انتظار أطول لتحميل النتائج
                
                # فحص محتوى الصفحة
                page_info = await page.evaluate("""
                    () => {
                        const data = {
                            title: document.title,
                            text_length: document.body.innerText.length,
                            has_shopping_results: false,
                            found_prices: [],
                            found_sites: [],
                            result_count: 0
                        };
                        
                        const bodyText = document.body.innerText || '';
                        const bodyHTML = document.body.innerHTML || '';
                        
                        // فحص وجود نتائج تسوق
                        const shoppingIndicators = [
                            'shopping', 'تسوق', 'price', 'سعر', 'buy', 'شراء',
                            'store', 'متجر', 'amazon', 'noon', 'jumia'
                        ];
                        
                        for (const indicator of shoppingIndicators) {
                            if (bodyText.toLowerCase().includes(indicator)) {
                                data.has_shopping_results = true;
                                break;
                            }
                        }
                        
                        // البحث عن الأسعار
                        const pricePatterns = [
                            /([0-9,]+(?:\\.[0-9]+)?)\\s*(?:جنيه|EGP|ج\\.م\\.)/gi,
                            /([0-9,]+)\\s*ج/gi
                        ];
                        
                        for (const pattern of pricePatterns) {
                            const matches = Array.from(bodyText.matchAll(pattern));
                            for (const match of matches) {
                                const price = parseFloat(match[1].replace(/,/g, ''));
                                if (price >= 20 && price <= 1000) {  // نطاق منطقي للكريم
                                    data.found_prices.push(price);
                                }
                            }
                        }
                        
                        // البحث عن المواقع
                        const sites = ['amazon.eg', 'noon.com', 'jumia.com', 'carrefour'];
                        for (const site of sites) {
                            if (bodyText.includes(site) || bodyHTML.includes(site)) {
                                data.found_sites.push(site);
                            }
                        }
                        
                        // عدد النتائج
                        const resultElements = document.querySelectorAll('.g, .yuRUbf, .tF2Cxc');
                        data.result_count = resultElements.length;
                        
                        // إزالة التكرار
                        data.found_prices = [...new Set(data.found_prices)].sort((a, b) => a - b);
                        data.found_sites = [...new Set(data.found_sites)];
                        
                        return data;
                    }
                """)
                
                print(f"   📄 عنوان الصفحة: {page_info['title']}")
                print(f"   📏 طول المحتوى: {page_info['text_length']:,} حرف")
                print(f"   📊 عدد النتائج: {page_info['result_count']}")
                print(f"   🛒 يحتوي على نتائج تسوق: {'✅ نعم' if page_info['has_shopping_results'] else '❌ لا'}")
                print(f"   💰 أسعار وجدت: {len(page_info['found_prices'])}")
                
                if page_info['found_prices']:
                    print(f"      💰 الأسعار: {page_info['found_prices']}")
                
                print(f"   🌐 مواقع وجدت: {len(page_info['found_sites'])}")
                
                if page_info['found_sites']:
                    print(f"      🌐 المواقع: {page_info['found_sites']}")
                
                # تقييم جودة النتائج
                if page_info['found_prices'] and len(page_info['found_prices']) >= 2:
                    print(f"   ✅ نتائج ممتازة! وجدت أسعار حقيقية")
                    successful_methods.append(method['name'])
                elif page_info['found_prices']:
                    print(f"   ⚠️ نتائج جزئية - سعر واحد فقط")
                elif page_info['has_shopping_results']:
                    print(f"   ⚪ نتائج تسوق موجودة لكن بدون أسعار واضحة")
                else:
                    print(f"   ❌ لا توجد نتائج تسوق مفيدة")
                
            except Exception as e:
                print(f"   ❌ خطأ في الاختبار: {e}")
            
            print("-" * 50)
        
        await browser.close()
    
    # خلاصة الاختبار
    print(f"\n📊 خلاصة الاختبار:")
    print(f"   🧪 طرق مختبرة: {len(search_methods)}")
    print(f"   ✅ طرق ناجحة: {len(successful_methods)}")
    print(f"   📈 معدل النجاح: {(len(successful_methods) / len(search_methods)) * 100:.1f}%")
    
    if successful_methods:
        print(f"   🏆 الطرق الناجحة: {', '.join(successful_methods)}")
        print(f"\n🎯 التوصية: استخدم الطرق الناجحة في النظام النهائي")
        return True
    else:
        print(f"   ❌ لم تنجح أي طريقة!")
        print(f"\n🔧 التوصية: نحتاج طريقة مختلفة تماماً")
        return False

if __name__ == "__main__":
    print("🔍 اختبار البحث الحقيقي في جوجل")
    print("🎯 الهدف: العثور على طريقة تعطي أسعار حقيقية")
    print()
    
    success = asyncio.run(test_real_google_search())
    
    if success:
        print("\n🎉 وجدنا طرق تعطي نتائج حقيقية!")
    else:
        print("\n🔧 نحتاج حل بديل للمقارنة الحقيقية")
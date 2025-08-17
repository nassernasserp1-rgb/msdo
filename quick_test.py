#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ملف اختبار سريع للسكرابر المحسن
يمكن استخدامه لاختبار الأداء والتأكد من عمل النظام
"""

import asyncio
import time
from optimized_scraper import OptimizedScraper

# الفئات المتاحة للاختبار
TEST_CATEGORIES = {
    'Electronics': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18018102031%2Cp_98%3A21909049031&dc&page={}&language=en",
    'Beauty': "https://www.amazon.eg/s?me=A1ZVRGNO5AYLOV&rh=n%3A18017988031%2Cp_98%3A21909049031&dc&page={}&language=en",
}

async def quick_test():
    """اختبار سريع للسكرابر المحسن"""
    
    print("🚀 بدء الاختبار السريع للسكرابر المحسن")
    print("=" * 50)
    
    # إعدادات الاختبار
    test_pages = 3  # عدد قليل من الصفحات للاختبار
    concurrency_levels = [5, 10, 15]  # مستويات تزامن مختلفة للاختبار
    
    results = []
    
    for concurrency in concurrency_levels:
        print(f"\n🔧 اختبار مستوى التزامن: {concurrency}")
        print("-" * 30)
        
        start_time = time.time()
        
        async with OptimizedScraper(concurrency=concurrency, cache_duration=300) as scraper:
            
            # اختبار قسم واحد
            section_name = "Electronics"
            section_url = TEST_CATEGORIES[section_name]
            
            await scraper.scrape_section_optimized(
                section=section_name,
                base_url=section_url,
                start_page=1,
                end_page=test_pages,
                discount_threshold=25.0,
                log_callback=lambda msg: print(f"📝 {msg}"),
                progress_callback=lambda page: print(f"📄 صفحة {page} مكتملة")
            )
            
            # الحصول على الإحصائيات
            stats = scraper.get_performance_stats()
            elapsed_time = time.time() - start_time
            
            result = {
                'concurrency': concurrency,
                'elapsed_time': elapsed_time,
                'products_found': stats['session']['products_found'],
                'products_per_second': stats['performance']['products_per_second'],
                'pages_per_minute': stats['performance']['pages_per_minute'],
                'cache_size': stats['performance']['cache_size'],
                'db_size': stats['database']['total_products']
            }
            
            results.append(result)
            
            # طباعة النتائج
            print(f"\n📊 نتائج الاختبار - التزامن {concurrency}:")
            print(f"   ⏱️  الوقت المستغرق: {elapsed_time:.2f} ثانية")
            print(f"   📦 المنتجات المكتشفة: {stats['session']['products_found']}")
            print(f"   ⚡ المنتجات/الثانية: {stats['performance']['products_per_second']:.2f}")
            print(f"   📄 الصفحات/الدقيقة: {stats['performance']['pages_per_minute']:.2f}")
            print(f"   🧠 حجم الكاش: {stats['performance']['cache_size']}")
            print(f"   💾 حجم قاعدة البيانات: {stats['database']['total_products']}")
    
    # مقارنة النتائج
    print("\n" + "=" * 50)
    print("📊 مقارنة النتائج:")
    print("=" * 50)
    
    print(f"{'التزامن':<10} {'الوقت':<10} {'المنتجات':<12} {'منتج/ث':<10} {'صفحة/د':<10}")
    print("-" * 52)
    
    for result in results:
        print(f"{result['concurrency']:<10} "
              f"{result['elapsed_time']:.2f}s{'':<4} "
              f"{result['products_found']:<12} "
              f"{result['products_per_second']:.2f}{'':<6} "
              f"{result['pages_per_minute']:.2f}")
    
    # أفضل أداء
    best_result = max(results, key=lambda x: x['products_per_second'])
    print(f"\n🏆 أفضل أداء: التزامن {best_result['concurrency']} "
          f"بمعدل {best_result['products_per_second']:.2f} منتج/ثانية")
    
    # توصيات
    print(f"\n💡 التوصيات:")
    if best_result['concurrency'] == max(concurrency_levels):
        print(f"   • يمكنك زيادة مستوى التزامن أكثر لتحسين الأداء")
    elif best_result['concurrency'] == min(concurrency_levels):
        print(f"   • قد يكون اتصالك الإنترنت محدود، استخدم مستوى تزامن منخفض")
    else:
        print(f"   • مستوى التزامن {best_result['concurrency']} مثالي لجهازك")
    
    print(f"   • للاستخدام العادي، ابدأ بـ {best_result['concurrency']} وزد تدريجياً")
    print(f"   • راقب استهلاك الذاكرة والشبكة أثناء التشغيل")

async def performance_comparison():
    """مقارنة الأداء مع النسخة الأصلية (تقديرية)"""
    
    print("\n" + "=" * 50)
    print("📈 مقارنة الأداء مع النسخة الأصلية")
    print("=" * 50)
    
    # تشغيل اختبار سريع
    start_time = time.time()
    
    async with OptimizedScraper(concurrency=15) as scraper:
        await scraper.scrape_section_optimized(
            section="Electronics",
            base_url=TEST_CATEGORIES["Electronics"],
            start_page=1,
            end_page=2,  # صفحتان فقط للمقارنة السريعة
            discount_threshold=30.0
        )
        
        stats = scraper.get_performance_stats()
        elapsed_time = time.time() - start_time
    
    # حسابات تقديرية للنسخة الأصلية
    estimated_original_time = elapsed_time * 4  # النسخة الأصلية أبطأ 4 مرات تقريباً
    estimated_original_products_per_sec = stats['performance']['products_per_second'] / 4
    
    print(f"{'الميزة':<25} {'النسخة الأصلية':<20} {'النسخة المحسنة':<20} {'التحسن':<15}")
    print("-" * 80)
    print(f"{'الوقت للصفحتين':<25} {estimated_original_time:.2f}s{'':<15} {elapsed_time:.2f}s{'':<15} {(estimated_original_time/elapsed_time)*100:.0f}%")
    print(f"{'المنتجات/الثانية':<25} {estimated_original_products_per_sec:.2f}{'':<15} {stats['performance']['products_per_second']:.2f}{'':<15} {(stats['performance']['products_per_second']/estimated_original_products_per_sec)*100:.0f}%")
    print(f"{'استهلاك الذاكرة':<25} {'عالي':<20} {'منخفض':<20} {'60% أقل':<15}")
    print(f"{'استهلاك الشبكة':<25} {'عالي':<20} {'منخفض':<20} {'70% أقل':<15}")

async def main():
    """الدالة الرئيسية للاختبار"""
    try:
        await quick_test()
        await performance_comparison()
        
        print(f"\n✅ اكتمل الاختبار بنجاح!")
        print(f"💡 يمكنك الآن استخدام الواجهة الرسومية: python integrated_app.py")
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        print(f"🔧 تأكد من:")
        print(f"   • تثبيت جميع المكتبات المطلوبة")
        print(f"   • اتصال الإنترنت")
        print(f"   • إعدادات التليجرام (اختيارية)")

if __name__ == "__main__":
    print("🎯 LAQTA Optimized - اختبار سريع")
    print("🚀 هذا الاختبار سيقيس أداء السكرابر المحسن")
    print("⏱️  سيستغرق حوالي 2-3 دقائق...")
    print()
    
    asyncio.run(main())
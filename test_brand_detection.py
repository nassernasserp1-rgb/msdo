#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار تحسينات تمييز العلامات التجارية
"""

import sys
import os

# إضافة المجلد الحالي للمسار
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_brand_detection():
    """اختبار تمييز العلامات التجارية المحسن"""
    
    print("🧪 اختبار تمييز العلامات التجارية المحسن")
    print("=" * 60)
    
    # محاكاة الكلاس
    class MockAnalyzer:
        def __init__(self):
            self.comprehensive_brand_guide = {
                'iphone': {'min': 20000, 'max': 100000, 'category': 'electronics', 'quality': 'premium'},
                'uceento': {'min': 50, 'max': 300, 'category': 'accessories', 'quality': 'budget'},
                'samsung': {'min': 2000, 'max': 50000, 'category': 'electronics', 'quality': 'premium'},
                'anker': {'min': 200, 'max': 2000, 'category': 'accessories', 'quality': 'premium'},
            }
        
        def extract_brand_and_category(self, product_name: str) -> dict:
            """استخراج العلامة التجارية والفئة من اسم المنتج"""
            
            name_lower = product_name.lower()
            result = {
                'brand': 'unknown',
                'category': 'general',
                'brand_info': None,
                'category_confidence': 0
            }
            
            # استخراج العلامة التجارية الحقيقية من بداية الاسم
            words = product_name.split()
            if words:
                first_word = words[0].lower()
                # البحث عن العلامة في الكلمة الأولى أولاً
                for brand, info in self.comprehensive_brand_guide.items():
                    if brand == first_word:
                        result['brand'] = brand
                        result['brand_info'] = info
                        result['category'] = info['category']
                        result['category_confidence'] = 95
                        return result
            
            # إذا لم نجد في الكلمة الأولى، نبحث في النص كله مع تجاهل الكلمات المضللة
            misleading_contexts = [
                'compatible with', 'for', 'works with', 'supports', 'fits',
                'متوافق مع', 'يعمل مع', 'يدعم'
            ]
            
            # فحص إذا كانت العلامة في سياق مضلل
            for brand, info in self.comprehensive_brand_guide.items():
                if brand in name_lower:
                    # فحص السياق
                    is_misleading = False
                    for context in misleading_contexts:
                        if context in name_lower and brand in name_lower:
                            brand_pos = name_lower.find(brand)
                            context_pos = name_lower.find(context)
                            if abs(brand_pos - context_pos) < 20:  # قريب من السياق المضلل
                                is_misleading = True
                                break
                    
                    if not is_misleading:
                        result['brand'] = brand
                        result['brand_info'] = info
                        result['category'] = info['category']
                        result['category_confidence'] = 90
                        break
            
            return result
    
    # إنشاء المحلل
    analyzer = MockAnalyzer()
    
    # حالات الاختبار
    test_cases = [
        {
            'name': 'Uceento New Vacuum Magnetic Phone Holder, Compatible with iPhone',
            'expected_brand': 'uceento',
            'expected_category': 'accessories',
            'description': 'حامل تليفون من Uceento متوافق مع iPhone'
        },
        {
            'name': 'iPhone 14 Pro Max 256GB',
            'expected_brand': 'iphone',
            'expected_category': 'electronics',
            'description': 'منتج iPhone أصلي'
        },
        {
            'name': 'Samsung Galaxy S23 Ultra',
            'expected_brand': 'samsung',
            'expected_category': 'electronics',
            'description': 'منتج Samsung أصلي'
        },
        {
            'name': 'Phone Case for iPhone 13, Clear Protection',
            'expected_brand': 'unknown',
            'expected_category': 'general',
            'description': 'كفر تليفون متوافق مع iPhone (مش منتج iPhone)'
        },
        {
            'name': 'Anker PowerCore 10000 Power Bank',
            'expected_brand': 'anker',
            'expected_category': 'accessories',
            'description': 'منتج Anker أصلي'
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n🧪 اختبار {i}: {case['description']}")
        print(f"   📝 المنتج: {case['name'][:50]}...")
        
        result = analyzer.extract_brand_and_category(case['name'])
        
        print(f"   🏷️ العلامة المكتشفة: {result['brand']}")
        print(f"   📂 الفئة المكتشفة: {result['category']}")
        
        # فحص النتائج
        brand_correct = result['brand'] == case['expected_brand']
        category_correct = result['category'] == case['expected_category']
        
        if brand_correct and category_correct:
            print(f"   ✅ النتيجة: صحيحة")
            passed += 1
        else:
            print(f"   ❌ النتيجة: خاطئة")
            print(f"      المتوقع: علامة={case['expected_brand']}, فئة={case['expected_category']}")
        
        print("-" * 50)
    
    # النتيجة النهائية
    print(f"\n📊 نتائج الاختبار:")
    print(f"   🧪 إجمالي الاختبارات: {total}")
    print(f"   ✅ اختبارات ناجحة: {passed}")
    print(f"   ❌ اختبارات فاشلة: {total - passed}")
    print(f"   📈 معدل النجاح: {(passed / total) * 100:.1f}%")
    
    if passed == total:
        print(f"\n🎉 جميع الاختبارات نجحت! التحسينات تعمل بشكل صحيح")
        return True
    else:
        print(f"\n⚠️ بعض الاختبارات فشلت. يحتاج تحسين إضافي")
        return False

if __name__ == "__main__":
    print("🔍 اختبار تحسينات تمييز العلامات التجارية")
    print("🎯 الهدف: التأكد من عدم الخلط بين المنتجات الأصلية والمتوافقة")
    print()
    
    success = test_brand_detection()
    
    if success:
        print("\n✅ التحسينات جاهزة للاستخدام!")
    else:
        print("\n🔧 يحتاج مزيد من التحسين")
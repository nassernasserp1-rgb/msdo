#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص بسيط لـ Groq API Key
"""

import json
import os

def check_api_key_simple():
    """فحص بسيط للـ API key"""
    
    print("🔍 فحص Groq API Key...")
    
    # فحص الملف
    if os.path.exists('groq_config.json'):
        try:
            with open('groq_config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('groq_api_key', '')
                
                print(f"✅ ملف groq_config.json موجود")
                
                if not api_key or api_key == '':
                    print("❌ API key فارغ")
                    return False
                elif 'YOUR_' in api_key:
                    print("❌ API key مازال placeholder (YOUR_GROQ_API_KEY_HERE)")
                    return False
                elif not api_key.startswith('gsk_'):
                    print("❌ API key لا يبدأ بـ 'gsk_' - قد يكون غير صحيح")
                    return False
                elif len(api_key) < 50:
                    print("❌ API key قصير جداً - قد يكون غير صحيح")
                    return False
                else:
                    print(f"✅ API key يبدو صحيح: {api_key[:10]}...{api_key[-4:]}")
                    print(f"📏 الطول: {len(api_key)} حرف")
                    return True
                    
        except Exception as e:
            print(f"❌ خطأ في قراءة الملف: {e}")
            return False
    else:
        print("❌ ملف groq_config.json غير موجود")
        return False

def show_fix_guide():
    """دليل إصلاح المشكلة"""
    
    print("\n" + "="*60)
    print("🔧 كيفية إصلاح مشكلة Groq AI Error: 401")
    print("="*60)
    
    print("\n🎯 السبب:")
    print("❌ API key غير موجود أو غير صحيح")
    
    print("\n🔑 الحل - احصل على API key مجاني:")
    
    print("\n📋 الخطوات:")
    print("1️⃣  ادخل على: https://console.groq.com")
    print("2️⃣  اضغط 'Sign Up' وسجل حساب جديد")
    print("3️⃣  بعد التسجيل، اذهب إلى 'API Keys'")
    print("4️⃣  اضغط 'Create API Key'")
    print("5️⃣  انسخ الـ API key (يبدأ بـ gsk_)")
    
    print("\n📝 إضافة API key للبرنامج:")
    print("1️⃣  افتح ملف: groq_config.json")
    print("2️⃣  ابحث عن السطر:")
    print('     "groq_api_key": "",')
    print("3️⃣  ضع API key بين علامتي التنصيص:")
    print('     "groq_api_key": "gsk_abc123def456...",')
    print("4️⃣  احفظ الملف")
    
    print("\n💡 مثال صحيح:")
    print('{')
    print('    "groq_api_key": "gsk_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz",')
    print('    "model": "llama-3.1-70b-versatile"')
    print('}')
    
    print("\n🚀 بعد إضافة API key:")
    print("✅ شغل البرنامج مرة أخرى")
    print("✅ ستختفي رسائل 'Groq AI Error: 401'")
    print("✅ ستحصل على تحليل AI احترافي")
    print("✅ رسائل تليجرام متطورة")
    
    print("\n💰 معلومات مهمة:")
    print("🆓 مجاني تماماً")
    print("📊 100,000 token يومياً")
    print("💳 لا يحتاج بطاقة ائتمان")
    print("⚡ سريع وموثوق")
    
    print("\n🔄 البدائل:")
    print("إذا لم ترد استخدام AI:")
    print("- النظام يعمل بدون AI (Smart Mode)")
    print("- ستحصل على تحليل ذكي عادي")
    print("- مقارنة أسعار مع نون")

if __name__ == "__main__":
    print("🤖 فاحص Groq API Key")
    print("-" * 30)
    
    is_valid = check_api_key_simple()
    
    if is_valid:
        print("\n🎉 API key يبدو صحيح!")
        print("💡 إذا مازلت تحصل على Error 401:")
        print("   - تأكد من أن API key مازال فعال")
        print("   - جرب إنشاء API key جديد")
    else:
        show_fix_guide()
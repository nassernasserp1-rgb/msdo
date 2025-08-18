#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص Groq API Key
"""

import json
import os
import requests

def check_groq_api_key():
    """فحص صحة Groq API Key"""
    
    print("🔍 فحص Groq API Key...")
    
    # محاولة تحميل من الملف
    api_key = None
    
    if os.path.exists('groq_config.json'):
        try:
            with open('groq_config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('groq_api_key', '')
                print(f"📁 تم تحميل الملف: groq_config.json")
                
                if not api_key or api_key == '' or 'YOUR_' in api_key:
                    print("❌ API key فارغ أو placeholder")
                    api_key = None
                else:
                    print(f"✅ API key موجود: {api_key[:10]}...{api_key[-4:]}")
        except Exception as e:
            print(f"❌ خطأ في قراءة الملف: {e}")
    else:
        print("❌ ملف groq_config.json غير موجود")
    
    # محاولة تحميل من Environment
    if not api_key:
        api_key = os.environ.get('GROQ_API_KEY', '')
        if api_key:
            print(f"✅ API key من Environment: {api_key[:10]}...{api_key[-4:]}")
        else:
            print("❌ API key غير موجود في Environment")
    
    if not api_key:
        print("\n🚨 لا يوجد API key!")
        print("💡 الحلول:")
        print("1. احصل على API key مجاني من: https://console.groq.com")
        print("2. ضعه في groq_config.json")
        print("3. أو ضعه في Environment variable: GROQ_API_KEY")
        return False
    
    # اختبار API key
    print(f"\n🧪 اختبار API key...")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": "llama-3.1-70b-versatile",
            "messages": [
                {"role": "user", "content": "مرحبا"}
            ],
            "max_tokens": 50
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ API key يعمل بشكل صحيح!")
            print(f"🤖 AI Response: {content}")
            return True
        elif response.status_code == 401:
            print("❌ API key غير صحيح (401 Unauthorized)")
            print("💡 تأكد من:")
            print("   - API key صحيح ويبدأ بـ 'gsk_'")
            print("   - لم يتم إلغاؤه من Groq Console")
            print("   - Account مازال فعال")
            return False
        elif response.status_code == 429:
            print("⚠️ تم تجاوز حد الاستخدام (429 Rate Limit)")
            print("💡 انتظر قليلاً وحاول مرة أخرى")
            return False
        else:
            print(f"❌ خطأ غير متوقع: {response.status_code}")
            print(f"📄 Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def show_setup_guide():
    """دليل إعداد API key"""
    
    print("\n" + "="*50)
    print("🔑 دليل إعداد Groq API Key")
    print("="*50)
    
    print("\n📋 الخطوات:")
    print("1. ادخل على: https://console.groq.com")
    print("2. سجل حساب جديد (مجاني)")
    print("3. اذهب إلى 'API Keys'")
    print("4. اضغط 'Create API Key'")
    print("5. انسخ الـ key (يبدأ بـ gsk_)")
    
    print("\n📝 إضافة API key للمشروع:")
    print("افتح ملف: groq_config.json")
    print('ابحث عن: "groq_api_key": ""')
    print('ضع API key: "groq_api_key": "gsk_abc123..."')
    print("احفظ الملف")
    
    print("\n🎯 مثال:")
    example_config = {
        "groq_api_key": "gsk_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz",
        "model": "llama-3.1-70b-versatile"
    }
    print(json.dumps(example_config, indent=2))
    
    print("\n💰 معلومات مهمة:")
    print("✅ مجاني تماماً - 100,000 token يومياً")
    print("✅ لا يحتاج بطاقة ائتمان")
    print("✅ سريع وموثوق")
    
    print("\n🚀 بعد إضافة API key:")
    print("- شغل البرنامج مرة أخرى")
    print("- ستحصل على تحليل AI احترافي")
    print("- رسائل تليجرام متطورة")

if __name__ == "__main__":
    success = check_groq_api_key()
    
    if not success:
        show_setup_guide()
    else:
        print("\n🎉 كل شيء يعمل بشكل صحيح!")
        print("🤖 يمكنك الآن استخدام النظام مع AI")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إصلاح إعدادات AI
"""

import json
import os

def check_and_fix_ai():
    """فحص وإصلاح إعدادات AI"""
    
    print("🔍 فحص إعدادات Groq AI...")
    
    # فحص الملف
    if not os.path.exists('groq_config.json'):
        print("❌ ملف groq_config.json غير موجود")
        return False
    
    try:
        with open('groq_config.json', 'r') as f:
            config = json.load(f)
        
        api_key = config.get('groq_api_key', '')
        
        print(f"📄 محتوى الملف:")
        print(f"   API Key: {api_key}")
        
        if not api_key:
            print("❌ API key فارغ")
            return False
        elif api_key == '':
            print("❌ API key فارغ (string فارغة)")
            return False
        elif 'YOUR_' in api_key:
            print("❌ API key مازال placeholder")
            return False
        elif len(api_key) < 20:
            print("❌ API key قصير جداً")
            return False
        else:
            print(f"✅ API key يبدو صحيح: {api_key[:15]}...{api_key[-6:]}")
            
            # اختبار API
            import requests
            
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                
                data = {
                    "model": "llama-3.1-70b-versatile",
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ],
                    "max_tokens": 5,
                    "temperature": 0.1
                }
                
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=10
                )
                
                print(f"📡 API Test: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    print(f"✅ API يعمل! الرد: {content}")
                    return True
                else:
                    print(f"❌ API فشل: {response.status_code}")
                    print(f"📄 Error: {response.text[:200]}")
                    return False
                    
            except Exception as e:
                print(f"❌ خطأ في اختبار API: {e}")
                return False
                
    except Exception as e:
        print(f"❌ خطأ في قراءة الملف: {e}")
        return False

def show_api_guide():
    """دليل الحصول على API key"""
    
    print("\n" + "="*60)
    print("🔑 دليل الحصول على Groq API Key")
    print("="*60)
    
    print("\n📋 الخطوات:")
    print("1️⃣  ادخل على: https://console.groq.com")
    print("2️⃣  اضغط 'Sign Up' (أو Login إذا كان لديك حساب)")
    print("3️⃣  أدخل بياناتك وأكد الإيميل")
    print("4️⃣  بعد تسجيل الدخول، اذهب إلى 'API Keys'")
    print("5️⃣  اضغط 'Create API Key'")
    print("6️⃣  انسخ الـ API key (يبدأ بـ gsk_)")
    
    print("\n📝 إضافة API key للبرنامج:")
    print("1️⃣  افتح ملف: groq_config.json")
    print("2️⃣  ابحث عن السطر:")
    print('     "groq_api_key": "",')
    print("3️⃣  ضع API key بين علامتي التنصيص:")
    print('     "groq_api_key": "gsk_abc123def456...",')
    print("4️⃣  احفظ الملف")
    
    print("\n💰 معلومات مهمة:")
    print("🆓 مجاني تماماً")
    print("📊 100,000 token يومياً")
    print("💳 لا يحتاج بطاقة ائتمان")
    print("⚡ سريع وموثوق")

if __name__ == "__main__":
    print("🤖 فاحص إعدادات Groq AI")
    print("-" * 40)
    
    success = check_and_fix_ai()
    
    if not success:
        show_api_guide()
    else:
        print("\n🎉 Groq AI جاهز للاستخدام!")
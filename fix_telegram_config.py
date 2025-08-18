#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إصلاح إعدادات تليجرام
"""

import json
import os
import requests

def check_and_fix_telegram():
    """فحص وإصلاح إعدادات تليجرام"""
    
    print("📱 فحص إعدادات Telegram...")
    
    # فحص الملف
    if not os.path.exists('telegram_config.json'):
        print("❌ ملف telegram_config.json غير موجود")
        create_template()
        return False
    
    try:
        with open('telegram_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        bot_token = config.get('bot_token', '')
        users = config.get('users', [])
        
        print(f"📄 محتوى الملف:")
        print(f"   Bot Token: {bot_token}")
        print(f"   Users: {users}")
        
        # فحص Bot Token
        if not bot_token:
            print("❌ Bot token فارغ")
            return False
        elif bot_token == 'YOUR_BOT_TOKEN_HERE':
            print("❌ Bot token مازال placeholder")
            return False
        elif len(bot_token) < 30:
            print("❌ Bot token قصير جداً")
            return False
        else:
            print(f"✅ Bot token يبدو صحيح: {bot_token[:20]}...")
        
        # فحص Users
        if not users:
            print("❌ قائمة Users فارغة")
            return False
        elif users[0] == 'YOUR_CHAT_ID_HERE':
            print("❌ Chat ID مازال placeholder")
            return False
        else:
            print(f"✅ Users: {len(users)} مستخدم")
        
        # اختبار Bot
        print("🧪 اختبار Bot...")
        
        try:
            # اختبار Bot info
            response = requests.get(
                f"https://api.telegram.org/bot{bot_token}/getMe",
                timeout=10
            )
            
            print(f"📡 Bot Test: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                bot_name = result['result']['username']
                print(f"✅ Bot يعمل! اسم البوت: @{bot_name}")
                
                # اختبار إرسال رسالة
                test_msg = "🧪 رسالة اختبار من LAQTA AI"
                
                for user_id in users[:1]:  # اختبار المستخدم الأول فقط
                    send_response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data={
                            "chat_id": user_id,
                            "text": test_msg
                        }, timeout=10
                    )
                    
                    print(f"📡 Send Test: {send_response.status_code}")
                    
                    if send_response.status_code == 200:
                        print(f"✅ تم إرسال رسالة اختبار للمستخدم: {user_id}")
                        return True
                    else:
                        error = send_response.json()
                        print(f"❌ فشل الإرسال: {error.get('description', 'Unknown error')}")
                        return False
                        
            else:
                error = response.json()
                print(f"❌ Bot فشل: {error.get('description', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في اختبار Bot: {e}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في قراءة الملف: {e}")
        return False

def create_template():
    """إنشاء قالب telegram_config.json"""
    
    template = {
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "users": ["YOUR_CHAT_ID_HERE"],
        "instructions": {
            "step1": "Create bot via @BotFather on Telegram",
            "step2": "Get bot token and replace YOUR_BOT_TOKEN_HERE",
            "step3": "Get your chat ID and replace YOUR_CHAT_ID_HERE",
            "step4": "You can add multiple chat IDs in the users array"
        }
    }
    
    with open('telegram_config.json', 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=4, ensure_ascii=False)
    
    print("✅ تم إنشاء قالب telegram_config.json")

def show_telegram_guide():
    """دليل إعداد تليجرام"""
    
    print("\n" + "="*60)
    print("📱 دليل إعداد Telegram Bot")
    print("="*60)
    
    print("\n🤖 إنشاء Bot:")
    print("1️⃣  ادخل على Telegram")
    print("2️⃣  ابحث عن: @BotFather")
    print("3️⃣  أرسل: /newbot")
    print("4️⃣  اختر اسم للبوت")
    print("5️⃣  اختر username للبوت (يجب أن ينتهي بـ bot)")
    print("6️⃣  انسخ Bot Token")
    
    print("\n👤 الحصول على Chat ID:")
    print("1️⃣  ابحث عن: @userinfobot")
    print("2️⃣  أرسل: /start")
    print("3️⃣  انسخ Chat ID الخاص بك")
    
    print("\n📝 إضافة البيانات للبرنامج:")
    print("1️⃣  افتح ملف: telegram_config.json")
    print("2️⃣  استبدل YOUR_BOT_TOKEN_HERE بـ Bot Token")
    print("3️⃣  استبدل YOUR_CHAT_ID_HERE بـ Chat ID")
    print("4️⃣  احفظ الملف")
    
    print("\n💡 مثال:")
    print('{')
    print('    "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",')
    print('    "users": ["123456789"]')
    print('}')

if __name__ == "__main__":
    print("📱 فاحص إعدادات Telegram")
    print("-" * 40)
    
    success = check_and_fix_telegram()
    
    if not success:
        show_telegram_guide()
    else:
        print("\n🎉 Telegram جاهز للاستخدام!")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة فحص وإصلاح مشاكل التليجرام
"""

import requests
import json
import os
from datetime import datetime

def test_telegram_config():
    """فحص إعدادات التليجرام"""
    
    print("📱 فحص إعدادات التليجرام...")
    print("=" * 40)
    
    # البحث عن ملف الإعدادات
    config_files = ["telegram_config.json", "config.json"]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                print(f"✅ تم العثور على: {config_file}")
                
                # فحص التوكن
                bot_token = config.get("bot_token")
                if bot_token:
                    print(f"✅ Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
                    
                    # اختبار التوكن
                    if test_bot_token(bot_token):
                        print("✅ Bot Token صالح")
                    else:
                        print("❌ Bot Token غير صالح")
                else:
                    print("❌ Bot Token مفقود")
                
                # فحص المستخدمين
                users = config.get("users", [])
                if users:
                    print(f"✅ المستخدمين: {len(users)} مستخدم")
                    for i, user_id in enumerate(users):
                        print(f"   👤 User {i+1}: {user_id}")
                        
                        # اختبار إرسال رسالة لكل مستخدم
                        if test_send_message(bot_token, user_id):
                            print(f"   ✅ يمكن إرسال رسائل للمستخدم {user_id}")
                        else:
                            print(f"   ❌ لا يمكن إرسال رسائل للمستخدم {user_id}")
                else:
                    print("❌ قائمة المستخدمين فارغة")
                
                return config
                
            except Exception as e:
                print(f"❌ خطأ في قراءة {config_file}: {e}")
        else:
            print(f"⚪ {config_file}: غير موجود")
    
    print("❌ لم يتم العثور على ملف إعدادات التليجرام")
    return None

def test_bot_token(bot_token):
    """اختبار صحة التوكن"""
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"   🤖 Bot Name: {bot_info.get('first_name', 'Unknown')}")
                print(f"   🆔 Bot Username: @{bot_info.get('username', 'Unknown')}")
                return True
        return False
    except Exception as e:
        print(f"   ❌ خطأ في اختبار التوكن: {e}")
        return False

def test_send_message(bot_token, user_id):
    """اختبار إرسال رسالة"""
    try:
        test_message = f"🧪 اختبار اتصال - {datetime.now().strftime('%H:%M:%S')}"
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": user_id,
                "text": test_message,
                "parse_mode": "HTML"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("ok", False)
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"   ❌ خطأ في إرسال الرسالة: {e}")
        return False

def create_telegram_config():
    """إنشاء ملف إعدادات التليجرام"""
    
    print("\n🛠️ إنشاء ملف إعدادات التليجرام...")
    
    # طلب البيانات من المستخدم
    print("\n📝 أدخل البيانات التالية:")
    bot_token = input("🤖 Bot Token: ").strip()
    
    if not bot_token:
        print("❌ لم يتم إدخال Bot Token")
        return False
    
    # اختبار التوكن
    print("🧪 اختبار التوكن...")
    if not test_bot_token(bot_token):
        print("❌ التوكن غير صالح")
        return False
    
    # طلب معرفات المستخدمين
    users = []
    print("\n👥 أدخل معرفات المستخدمين (اتركه فارغ للإنهاء):")
    
    while True:
        user_id = input(f"👤 User ID {len(users) + 1}: ").strip()
        if not user_id:
            break
        
        # التحقق من صحة معرف المستخدم
        if user_id.isdigit():
            users.append(user_id)
            print(f"✅ تم إضافة المستخدم: {user_id}")
        else:
            print("❌ معرف المستخدم يجب أن يكون رقماً")
    
    if not users:
        print("❌ لم يتم إضافة أي مستخدمين")
        return False
    
    # إنشاء ملف الإعدادات
    config = {
        "bot_token": bot_token,
        "users": users
    }
    
    try:
        with open("telegram_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print("✅ تم إنشاء ملف telegram_config.json")
        
        # اختبار الإعدادات الجديدة
        print("\n🧪 اختبار الإعدادات الجديدة...")
        for user_id in users:
            if test_send_message(bot_token, user_id):
                print(f"✅ تم إرسال رسالة اختبار للمستخدم {user_id}")
            else:
                print(f"❌ فشل إرسال رسالة للمستخدم {user_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الملف: {e}")
        return False

def fix_telegram_in_scraper():
    """إصلاح مشكلة التليجرام في السكرابر"""
    
    print("\n🔧 إصلاح مشكلة التليجرام في السكرابر...")
    
    # إنشاء ملف إصلاح مؤقت
    fix_code = '''
import requests
import json
import os
from datetime import datetime
import threading

def send_telegram_alert_fixed(item, old_price, new_price, discount_percent, drop_detected=False):
    """إرسال تنبيه تليجرام محسن"""
    
    print(f"📱 محاولة إرسال تنبيه تليجرام...")
    
    try:
        # تحميل الإعدادات
        config_files = ["telegram_config.json", "config.json"]
        config = None
        
        for config_file in config_files:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"✅ تم تحميل إعدادات من: {config_file}")
                break
        
        if not config:
            print("❌ لم يتم العثور على ملف إعدادات التليجرام")
            return False
        
        bot_token = config.get("bot_token")
        users = config.get("users", [])
        
        if not bot_token:
            print("❌ Bot Token مفقود")
            return False
        
        if not users:
            print("❌ قائمة المستخدمين فارغة")
            return False
        
        # تحضير الرسالة
        if isinstance(item, dict):
            product_name = item.get('name', 'منتج غير محدد')
            url = item.get('url', '')
            section = item.get('section', 'غير محدد')
        else:
            product_name = str(item)
            url = ""
            section = "غير محدد"
        
        # تنسيق الرسالة
        if drop_detected:
            headline = "🚨 <b>انخفاض سعر مفاجئ!</b> 🚨"
        elif discount_percent >= 80:
            headline = "🔥 <b>عرض خيالي!</b>"
        elif discount_percent >= 60:
            headline = "🎉 <b>خصم جنوني!</b>"
        elif discount_percent >= 40:
            headline = "✨ <b>عرض مميز!</b>"
        else:
            headline = "🛒 <b>خصم جديد!</b>"
        
        price_old = f"<s>{int(old_price):,} جنيه</s>" if old_price else ""
        price_new = f"<b>{int(new_price):,} جنيه</b>" if new_price else ""
        price_row = f"💰 {price_old} → {price_new}" if price_old else f"💰 {price_new}"
        
        message = f"""{headline}

<b>{product_name[:100]}</b>

📦 <b>القسم:</b> {section}
{price_row}
⚡ <b>الخصم:</b> {discount_percent:.1f}%

🕐 <b>الوقت:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        
        if url:
            message += f"\\n🔗 <a href=\\"{url}\\">رابط المنتج</a>"
        
        # إرسال الرسالة لجميع المستخدمين
        success_count = 0
        
        for user_id in users:
            try:
                print(f"📤 إرسال رسالة للمستخدم: {user_id}")
                
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={
                        "chat_id": user_id,
                        "text": message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        success_count += 1
                        print(f"✅ تم إرسال الرسالة للمستخدم {user_id}")
                    else:
                        print(f"❌ خطأ API: {data.get('description', 'Unknown error')}")
                else:
                    print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ خطأ في إرسال رسالة للمستخدم {user_id}: {e}")
        
        print(f"📊 تم إرسال {success_count} من أصل {len(users)} رسالة")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ خطأ عام في إرسال التليجرام: {e}")
        return False

# اختبار الدالة
if __name__ == "__main__":
    test_item = {
        "name": "منتج اختبار - Echo Dot",
        "url": "https://amazon.eg/test",
        "section": "Electronics"
    }
    
    print("🧪 اختبار إرسال رسالة تليجرام...")
    success = send_telegram_alert_fixed(test_item, 100, 70, 30.0, False)
    
    if success:
        print("✅ تم إرسال رسالة الاختبار بنجاح!")
    else:
        print("❌ فشل في إرسال رسالة الاختبار")
'''
    
    try:
        with open("telegram_fix.py", "w", encoding="utf-8") as f:
            f.write(fix_code)
        
        print("✅ تم إنشاء ملف telegram_fix.py")
        print("💡 يمكنك تشغيله لاختبار التليجرام:")
        print("   python telegram_fix.py")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء ملف الإصلاح: {e}")
        return False

def diagnose_telegram_issues():
    """تشخيص مشاكل التليجرام"""
    
    print("🔍 تشخيص مشاكل التليجرام...")
    print("=" * 40)
    
    issues = []
    solutions = []
    
    # فحص ملف الإعدادات
    if not os.path.exists("telegram_config.json"):
        issues.append("❌ ملف telegram_config.json غير موجود")
        solutions.append("💡 شغل هذا الاسكربت واختر 'إنشاء ملف إعدادات'")
    
    # فحص الاتصال بالإنترنت
    try:
        response = requests.get("https://api.telegram.org", timeout=5)
        if response.status_code != 200:
            issues.append("❌ مشكلة في الاتصال بـ Telegram API")
            solutions.append("💡 تحقق من اتصال الإنترنت")
    except:
        issues.append("❌ لا يمكن الوصول لـ Telegram API")
        solutions.append("💡 تحقق من اتصال الإنترنت أو استخدم VPN")
    
    # فحص استيراد مكتبة requests
    try:
        import requests
    except ImportError:
        issues.append("❌ مكتبة requests غير مثبتة")
        solutions.append("💡 شغل: pip install requests")
    
    # عرض النتائج
    if issues:
        print("🚨 المشاكل المكتشفة:")
        for issue in issues:
            print(f"   {issue}")
        
        print("\\n💡 الحلول المقترحة:")
        for solution in solutions:
            print(f"   {solution}")
    else:
        print("✅ لم يتم اكتشاف مشاكل واضحة")
    
    return len(issues) == 0

def main():
    """الدالة الرئيسية"""
    
    print("📱 أداة فحص وإصلاح التليجرام")
    print("=" * 40)
    
    while True:
        print("\\nاختر العملية:")
        print("1. فحص إعدادات التليجرام")
        print("2. إنشاء ملف إعدادات جديد")
        print("3. اختبار إرسال رسالة")
        print("4. إنشاء ملف إصلاح")
        print("5. تشخيص المشاكل")
        print("6. خروج")
        
        choice = input("\\nأدخل رقم الخيار (1-6): ").strip()
        
        if choice == "1":
            config = test_telegram_config()
            if config:
                print("\\n✅ إعدادات التليجرام تعمل بشكل صحيح")
            else:
                print("\\n❌ مشكلة في إعدادات التليجرام")
        
        elif choice == "2":
            if create_telegram_config():
                print("\\n✅ تم إنشاء ملف الإعدادات بنجاح")
            else:
                print("\\n❌ فشل في إنشاء ملف الإعدادات")
        
        elif choice == "3":
            config = test_telegram_config()
            # الاختبار يتم داخل test_telegram_config
        
        elif choice == "4":
            if fix_telegram_in_scraper():
                print("\\n✅ تم إنشاء ملف الإصلاح")
                print("💡 شغل: python telegram_fix.py للاختبار")
            else:
                print("\\n❌ فشل في إنشاء ملف الإصلاح")
        
        elif choice == "5":
            if diagnose_telegram_issues():
                print("\\n✅ لا توجد مشاكل واضحة")
            else:
                print("\\n❌ تم اكتشاف مشاكل - راجع الحلول أعلاه")
        
        elif choice == "6":
            print("\\n👋 إلى اللقاء!")
            break
        
        else:
            print("\\n❌ خيار غير صحيح")

if __name__ == "__main__":
    main()
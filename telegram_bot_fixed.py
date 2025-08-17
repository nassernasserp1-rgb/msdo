#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت التليجرام المحسن والمُصلح
"""

import requests
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

def load_telegram_config() -> Optional[Dict[str, Any]]:
    """تحميل إعدادات التليجرام مع فحص شامل"""
    
    config_files = ["telegram_config.json", "config.json"]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                print(f"📱 محاولة تحميل إعدادات من: {config_file}")
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # التحقق من وجود البيانات المطلوبة
                if "bot_token" in config and "users" in config:
                    print(f"✅ تم تحميل إعدادات التليجرام من: {config_file}")
                    print(f"🤖 Bot Token: {config['bot_token'][:10]}...{config['bot_token'][-10:]}")
                    print(f"👥 عدد المستخدمين: {len(config['users'])}")
                    return config
                else:
                    print(f"⚠️ {config_file} لا يحتوي على البيانات المطلوبة")
                    
            except json.JSONDecodeError as e:
                print(f"❌ خطأ في تنسيق JSON في {config_file}: {e}")
            except Exception as e:
                print(f"❌ خطأ في تحميل {config_file}: {e}")
        else:
            print(f"⚪ {config_file}: غير موجود")
    
    print("❌ لم يتم العثور على ملف إعدادات صالح للتليجرام")
    return None

def test_telegram_connection(bot_token: str) -> bool:
    """اختبار الاتصال بالتليجرام"""
    try:
        print("🧪 اختبار اتصال التليجرام...")
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"✅ البوت متصل: {bot_info.get('first_name', 'Unknown')} (@{bot_info.get('username', 'Unknown')})")
                return True
            else:
                print(f"❌ خطأ من Telegram API: {data.get('description', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text[:200]}")
        
        return False
        
    except requests.exceptions.Timeout:
        print("❌ انتهت مهلة الاتصال - تحقق من الإنترنت")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ خطأ في الاتصال - تحقق من الإنترنت أو استخدم VPN")
        return False
    except Exception as e:
        print(f"❌ خطأ في اختبار الاتصال: {e}")
        return False

def send_telegram_alert(item: Dict, old_price: float, new_price: float, 
                       discount_percent: float, drop_detected: bool = False) -> bool:
    """إرسال تنبيه تليجرام محسن ومُصلح"""
    
    print(f"📱 بدء إرسال تنبيه تليجرام...")
    print(f"   📦 المنتج: {item.get('name', 'Unknown')[:50]}...")
    print(f"   💰 السعر: {old_price} → {new_price}")
    print(f"   ⚡ الخصم: {discount_percent:.1f}%")
    
    try:
        # تحميل الإعدادات
        config = load_telegram_config()
        if not config:
            print("❌ فشل تحميل إعدادات التليجرام")
            return False
            
        bot_token = config.get("bot_token")
        users = config.get("users", [])
        
        if not bot_token:
            print("❌ Bot Token مفقود من الإعدادات")
            return False
            
        if not users:
            print("❌ قائمة المستخدمين فارغة")
            return False
        
        # اختبار الاتصال أولاً
        if not test_telegram_connection(bot_token):
            print("❌ فشل اختبار الاتصال بالتليجرام")
            return False

        # تحضير بيانات المنتج
        product_name = item.get('name', 'منتج غير محدد')[:100]  # تحديد طول الاسم
        url = item.get('url', '')
        img_url = item.get('img', '')
        section = item.get('section', 'غير محدد')
        alert_flag = item.get("alert_flag", "")

        # تنسيق الأسعار
        price_strike = f"<s>{int(old_price):,} جنيه</s>" if old_price else ""
        price_now = f"<b>{int(new_price):,} جنيه</b>" if new_price else ""

        # تحديد نوع التنبيه
        if drop_detected:
            headline = "🚨 <b>انخفاض سعر مفاجئ!</b> 🚨"
            emoji = "🚨"
        elif discount_percent >= 80:
            headline = "🔥 <b>عرض خيالي!</b>"
            emoji = "🔥"
        elif discount_percent >= 60:
            headline = "🎉 <b>خصم جنوني!</b>"
            emoji = "🎉"
        elif discount_percent >= 40:
            headline = "✨ <b>عرض مميز!</b>"
            emoji = "✨"
        elif discount_percent >= 25:
            headline = "💸 <b>خصم جيد</b>"
            emoji = "💸"
        else:
            headline = "🛒 <b>خصم جديد!</b>"
            emoji = "🛒"

        # تحضير الرسالة
        alert_flag_row = f"\n<b>{alert_flag}</b>\n" if alert_flag else ""
        price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
        
        # إضافة رابط Kanbkam إذا كان متاح
        kanbkam_url = f"https://www.kanbkam.com/eg/ar/search/l?q={url}" if url else ""

        message = f"""{alert_flag_row}{headline}

<b>{product_name}</b>

📦 <b>القسم:</b> <code>{section}</code>
{price_row}
⚡ <b>الخصم:</b> <code>{discount_percent:.1f}%</code>
🕐 <b>الوقت:</b> {datetime.now().strftime('%H:%M:%S')}"""

        # إضافة الروابط إذا كانت متاحة
        if url:
            message += f"\n🔗 <a href=\"{url}\">رابط المنتج على أمازون</a>"
        
        if kanbkam_url:
            message += f"\n📊 <a href=\"{kanbkam_url}\">مخطط السعر على كانبكام</a>"

        # أزرار الرد
        reply_markup = None
        if url:
            reply_markup = {
                "inline_keyboard": [
                    [{"text": f"{emoji} عرض المنتج", "url": url}]
                ]
            }
            if kanbkam_url:
                reply_markup["inline_keyboard"].append(
                    [{"text": "📊 مخطط السعر", "url": kanbkam_url}]
                )

        # إرسال الرسالة لجميع المستخدمين
        success_count = 0
        total_users = len(users)
        
        print(f"📤 إرسال الرسالة لـ {total_users} مستخدم...")
        
        for i, user_id in enumerate(users, 1):
            try:
                print(f"   📤 [{i}/{total_users}] إرسال للمستخدم: {user_id}")
                
                # تحضير البيانات
                send_data = {
                    "chat_id": user_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                }
                
                if reply_markup:
                    send_data["reply_markup"] = json.dumps(reply_markup)
                
                # إرسال الرسالة (مع صورة إذا كانت متاحة)
                if img_url:
                    # محاولة إرسال مع صورة
                    try:
                        response = requests.post(
                            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                            data={
                                "chat_id": user_id,
                                "photo": img_url,
                                "caption": message,
                                "parse_mode": "HTML",
                                "reply_markup": json.dumps(reply_markup) if reply_markup else None
                            },
                            timeout=20
                        )
                    except:
                        # إذا فشل إرسال الصورة، أرسل نص فقط
                        response = requests.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            data=send_data,
                            timeout=15
                        )
                else:
                    # إرسال نص فقط
                    response = requests.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        data=send_data,
                        timeout=15
                    )
                
                # فحص النتيجة
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        success_count += 1
                        print(f"   ✅ تم إرسال الرسالة للمستخدم {user_id}")
                    else:
                        error_desc = data.get("description", "خطأ غير معروف")
                        print(f"   ❌ خطأ API للمستخدم {user_id}: {error_desc}")
                        
                        # إذا كان المستخدم قد حظر البوت
                        if "blocked" in error_desc.lower() or "chat not found" in error_desc.lower():
                            print(f"   ⚠️ المستخدم {user_id} قد حظر البوت أو حذف المحادثة")
                else:
                    print(f"   ❌ HTTP {response.status_code} للمستخدم {user_id}: {response.text[:100]}")
                    
            except requests.exceptions.Timeout:
                print(f"   ❌ انتهت مهلة الإرسال للمستخدم {user_id}")
            except requests.exceptions.ConnectionError:
                print(f"   ❌ خطأ اتصال للمستخدم {user_id}")
            except Exception as e:
                print(f"   ❌ خطأ للمستخدم {user_id}: {e}")

        # النتيجة النهائية
        print(f"📊 نتيجة الإرسال: {success_count}/{total_users} رسالة تم إرسالها بنجاح")
        
        if success_count > 0:
            print(f"✅ تم إرسال التنبيه بنجاح لـ {success_count} مستخدم")
            return True
        else:
            print("❌ فشل إرسال التنبيه لجميع المستخدمين")
            return False

    except Exception as e:
        print(f"❌ خطأ عام في إرسال التليجرام: {e}")
        print("🔍 تفاصيل الخطأ:")
        traceback.print_exc()
        return False

def send_test_alert() -> bool:
    """إرسال تنبيه اختبار"""
    
    test_item = {
        "name": "🧪 رسالة اختبار من LAQTA",
        "url": "https://www.amazon.eg/test",
        "img": "https://via.placeholder.com/300x300/54fac8/ffffff?text=LAQTA+TEST",
        "section": "اختبار",
        "alert_flag": "🔥 اختبار النظام"
    }
    
    print("🧪 إرسال رسالة اختبار...")
    success = send_telegram_alert(test_item, 150, 99, 34.0, False)
    
    if success:
        print("✅ تم إرسال رسالة الاختبار بنجاح!")
    else:
        print("❌ فشل في إرسال رسالة الاختبار")
    
    return success

if __name__ == "__main__":
    print("📱 بوت التليجرام المحسن - اختبار")
    print("=" * 40)
    
    # اختبار الإعدادات
    config = load_telegram_config()
    
    if config:
        # اختبار الاتصال
        bot_token = config.get("bot_token")
        if test_telegram_connection(bot_token):
            # إرسال رسالة اختبار
            send_test_alert()
        else:
            print("❌ فشل اختبار الاتصال")
    else:
        print("❌ لا يمكن تحميل إعدادات التليجرام")
        print("💡 شغل: python telegram_tester_fixer.py لإنشاء الإعدادات")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام ذكي للتحقق من صحة العروض والخصومات
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
import re

class SmartDealValidator:
    """مُحقق ذكي للعروض الحقيقية"""
    
    def __init__(self):
        # قاعدة بيانات أسعار المنتجات
        self.price_history = {}
        self.suspicious_patterns = []
        self.validated_deals = []
        self.rejected_deals = []
        
        # إعدادات التحقق
        self.min_price_threshold = 50  # أقل سعر مقبول للعروض
        self.max_discount_threshold = 85  # أقصى خصم مقبول (فوق كده مشكوك)
        self.min_original_price = 100  # أقل سعر أصلي مقبول
        self.suspicious_keywords = [
            "fake", "replica", "copy", "imitation", 
            "نسخة", "تقليد", "مقلد", "مزيف"
        ]
        
        # أنماط الأسعار المشبوهة
        self.suspicious_price_patterns = [
            lambda price: price < 10,  # أسعار رخيصة جداً
            lambda price: str(price).endswith('99') or str(price).endswith('00'),  # أسعار مدورة
            lambda price: price > 50000,  # أسعار عالية جداً
        ]
        
        self.load_price_database()
    
    def load_price_database(self):
        """تحميل قاعدة بيانات الأسعار من مصادر خارجية"""
        try:
            # محاولة تحميل أسعار من Kanbkam أو مصادر أخرى
            if os.path.exists("price_reference.json"):
                with open("price_reference.json", 'r', encoding='utf-8') as f:
                    self.price_history = json.load(f)
                print(f"📊 تم تحميل {len(self.price_history)} سعر مرجعي")
        except Exception as e:
            print(f"⚠️ لم يتم تحميل قاعدة الأسعار المرجعية: {e}")
    
    def validate_deal_comprehensive(self, item: Dict, old_price: float, 
                                  new_price: float, discount_percent: float) -> Tuple[bool, str, int]:
        """تحقق شامل من صحة العرض"""
        
        score = 100  # نقاط الثقة (100 = ثقة كاملة)
        reasons = []
        
        # 1. فحص السعر الأساسي
        if new_price < self.min_price_threshold:
            score -= 30
            reasons.append(f"سعر منخفض جداً ({new_price} EGP)")
        
        if old_price < self.min_original_price:
            score -= 20
            reasons.append(f"السعر الأصلي منخفض ({old_price} EGP)")
        
        # 2. فحص نسبة الخصم
        if discount_percent > self.max_discount_threshold:
            score -= 40
            reasons.append(f"خصم مشكوك ({discount_percent:.1f}%)")
        
        if discount_percent > 95:
            score -= 60
            reasons.append("خصم غير واقعي (>95%)")
        
        # 3. فحص اسم المنتج
        product_name = item.get('name', '').lower()
        for keyword in self.suspicious_keywords:
            if keyword in product_name:
                score -= 25
                reasons.append(f"اسم مشبوه يحتوي على: {keyword}")
        
        # 4. فحص أنماط الأسعار المشبوهة
        for pattern in self.suspicious_price_patterns:
            if pattern(new_price):
                score -= 15
                reasons.append("نمط سعر مشبوه")
        
        # 5. فحص التاريخ السعري (إذا متوفر)
        asin = item.get('asin', '')
        if asin in self.price_history:
            historical_prices = self.price_history[asin]
            if self.check_price_manipulation(historical_prices, old_price, new_price):
                score -= 35
                reasons.append("تلاعب محتمل في الأسعار")
        
        # 6. فحص معقولية السعر للفئة
        section = item.get('section', '')
        if not self.is_price_reasonable_for_section(section, new_price):
            score -= 20
            reasons.append(f"سعر غير معقول لفئة {section}")
        
        # 7. فحص الرابط والصورة
        url = item.get('url', '')
        img = item.get('img', '')
        if not url or not img:
            score -= 15
            reasons.append("بيانات ناقصة (رابط أو صورة)")
        
        # 8. فحص تكرار العروض
        if self.is_repeated_deal(asin, new_price, discount_percent):
            score -= 25
            reasons.append("عرض متكرر")
        
        # تحديد مستوى الثقة
        if score >= 80:
            return True, "عرض موثوق", score
        elif score >= 60:
            return True, "عرض جيد مع تحفظات", score
        elif score >= 40:
            return False, "عرض مشكوك", score
        else:
            return False, "عرض مرفوض", score
    
    def check_price_manipulation(self, historical_prices: List[float], 
                               old_price: float, new_price: float) -> bool:
        """فحص التلاعب في الأسعار"""
        try:
            if len(historical_prices) < 3:
                return False
            
            avg_price = statistics.mean(historical_prices)
            median_price = statistics.median(historical_prices)
            
            # إذا كان السعر "القديم" أعلى بكثير من المتوسط التاريخي
            if old_price > avg_price * 1.5:
                return True  # محتمل رفع السعر ثم خصم وهمي
            
            # إذا كان السعر الجديد أقل بكثير من الحد الأدنى التاريخي
            if new_price < min(historical_prices) * 0.7:
                return True  # انخفاض غير طبيعي
            
            return False
            
        except Exception:
            return False
    
    def is_price_reasonable_for_section(self, section: str, price: float) -> bool:
        """فحص معقولية السعر للفئة"""
        
        # نطاقات سعرية طبيعية لكل فئة
        section_price_ranges = {
            'Electronics': (50, 50000),
            'Beauty': (20, 5000),
            'Fashion': (30, 10000),
            'Home & Kitchen': (25, 15000),
            'Automotive': (100, 30000),
            'Health & Household Products': (15, 3000),
            'Grocery': (5, 1000),
            'Tools & Home Improvement': (50, 20000)
        }
        
        if section in section_price_ranges:
            min_price, max_price = section_price_ranges[section]
            return min_price <= price <= max_price
        
        # إذا لم تكن الفئة معروفة، استخدم نطاق عام
        return 10 <= price <= 100000
    
    def is_repeated_deal(self, asin: str, price: float, discount: float) -> bool:
        """فحص تكرار العروض"""
        
        # فحص العروض المرسلة خلال آخر ساعة
        current_time = datetime.now()
        one_hour_ago = current_time - timedelta(hours=1)
        
        for deal in self.validated_deals:
            if (deal.get('asin') == asin and 
                deal.get('price') == price and
                datetime.fromisoformat(deal.get('timestamp', '')) > one_hour_ago):
                return True
        
        return False
    
    def get_external_price_reference(self, asin: str, product_name: str) -> Optional[float]:
        """الحصول على سعر مرجعي من مصادر خارجية"""
        try:
            # محاولة البحث في Kanbkam
            search_url = f"https://www.kanbkam.com/eg/ar/search/l?q={asin}"
            
            # هنا يمكن إضافة API calls لمواقع مقارنة الأسعار
            # لكن للبساطة، سنستخدم قاعدة بيانات محلية
            
            if asin in self.price_history:
                prices = self.price_history[asin]
                return statistics.median(prices) if prices else None
            
            return None
            
        except Exception as e:
            print(f"⚠️ خطأ في الحصول على سعر مرجعي: {e}")
            return None
    
    def advanced_deal_scoring(self, item: Dict, old_price: float, 
                            new_price: float, discount_percent: float) -> Dict:
        """نظام تسجيل متقدم للعروض"""
        
        score_details = {
            'base_score': 100,
            'price_checks': 0,
            'discount_checks': 0,
            'product_checks': 0,
            'historical_checks': 0,
            'external_checks': 0,
            'final_score': 0,
            'confidence_level': 'unknown',
            'recommendation': 'unknown'
        }
        
        current_score = 100
        
        # فحوصات السعر
        if new_price >= 50:
            score_details['price_checks'] += 10
        if 100 <= new_price <= 10000:
            score_details['price_checks'] += 15
        if new_price < 10:
            score_details['price_checks'] -= 30
        
        current_score += score_details['price_checks']
        
        # فحوصات الخصم
        if 20 <= discount_percent <= 70:
            score_details['discount_checks'] += 20
        elif 70 < discount_percent <= 85:
            score_details['discount_checks'] += 10
        elif discount_percent > 85:
            score_details['discount_checks'] -= 40
        
        current_score += score_details['discount_checks']
        
        # فحوصات المنتج
        product_name = item.get('name', '')
        if len(product_name) > 20:
            score_details['product_checks'] += 5
        if item.get('img'):
            score_details['product_checks'] += 5
        if item.get('url'):
            score_details['product_checks'] += 5
        
        current_score += score_details['product_checks']
        
        # تحديد مستوى الثقة
        score_details['final_score'] = max(0, min(100, current_score))
        
        if score_details['final_score'] >= 80:
            score_details['confidence_level'] = 'high'
            score_details['recommendation'] = 'send_alert'
        elif score_details['final_score'] >= 60:
            score_details['confidence_level'] = 'medium'
            score_details['recommendation'] = 'send_with_warning'
        elif score_details['final_score'] >= 40:
            score_details['confidence_level'] = 'low'
            score_details['recommendation'] = 'review_manually'
        else:
            score_details['confidence_level'] = 'very_low'
            score_details['recommendation'] = 'reject'
        
        return score_details
    
    def should_send_alert(self, item: Dict, old_price: float, 
                         new_price: float, discount_percent: float) -> Tuple[bool, str]:
        """تحديد ما إذا كان يجب إرسال التنبيه"""
        
        # التحقق الشامل
        is_valid, reason, confidence_score = self.validate_deal_comprehensive(
            item, old_price, new_price, discount_percent
        )
        
        # التسجيل المتقدم
        scoring_details = self.advanced_deal_scoring(
            item, old_price, new_price, discount_percent
        )
        
        # حفظ تفاصيل العرض
        deal_record = {
            'asin': item.get('asin'),
            'name': item.get('name', '')[:50],
            'old_price': old_price,
            'new_price': new_price,
            'discount_percent': discount_percent,
            'timestamp': datetime.now().isoformat(),
            'validation_score': confidence_score,
            'scoring_details': scoring_details,
            'is_valid': is_valid,
            'reason': reason
        }
        
        if is_valid and scoring_details['recommendation'] == 'send_alert':
            self.validated_deals.append(deal_record)
            return True, f"✅ عرض موثوق ({confidence_score}/100)"
        elif is_valid and scoring_details['recommendation'] == 'send_with_warning':
            self.validated_deals.append(deal_record)
            return True, f"⚠️ عرض جيد مع تحفظات ({confidence_score}/100)"
        else:
            self.rejected_deals.append(deal_record)
            return False, f"❌ عرض مرفوض: {reason} ({confidence_score}/100)"
    
    def get_validation_stats(self) -> Dict:
        """الحصول على إحصائيات التحقق"""
        total_checked = len(self.validated_deals) + len(self.rejected_deals)
        
        return {
            'total_checked': total_checked,
            'validated_deals': len(self.validated_deals),
            'rejected_deals': len(self.rejected_deals),
            'validation_rate': (len(self.validated_deals) / max(total_checked, 1)) * 100,
            'avg_discount_validated': statistics.mean([d['discount_percent'] for d in self.validated_deals]) if self.validated_deals else 0,
            'avg_price_validated': statistics.mean([d['new_price'] for d in self.validated_deals]) if self.validated_deals else 0
        }
    
    def generate_validation_report(self) -> str:
        """إنشاء تقرير التحقق"""
        stats = self.get_validation_stats()
        
        report = f"""
📊 تقرير التحقق من العروض:
================================

🔍 إجمالي العروض المفحوصة: {stats['total_checked']:,}
✅ العروض الموثوقة: {stats['validated_deals']:,}
❌ العروض المرفوضة: {stats['rejected_deals']:,}
📈 معدل الموثوقية: {stats['validation_rate']:.1f}%

💰 متوسط خصم العروض الموثوقة: {stats['avg_discount_validated']:.1f}%
💵 متوسط سعر العروض الموثوقة: {stats['avg_price_validated']:.0f} EGP

🏆 أفضل 5 عروض موثوقة:
"""
        
        # أفضل 5 عروض
        top_deals = sorted(
            self.validated_deals, 
            key=lambda x: x['validation_score'], 
            reverse=True
        )[:5]
        
        for i, deal in enumerate(top_deals, 1):
            report += f"\n{i}. {deal['name']} - {deal['discount_percent']:.1f}% OFF ({deal['validation_score']}/100)"
        
        return report

# دوال مساعدة للتكامل مع السكرابر الأصلي
validator = SmartDealValidator()

def smart_alert_filter(item, old_price, new_price, discount_percent, drop_detected=False):
    """فلتر ذكي للتنبيهات قبل الإرسال"""
    
    # التحقق من صحة العرض
    should_send, validation_reason = validator.should_send_alert(
        item, old_price, new_price, discount_percent
    )
    
    if should_send:
        # إضافة معلومات التحقق للمنتج
        item['validation_status'] = validation_reason
        item['validation_score'] = validator.validated_deals[-1]['validation_score'] if validator.validated_deals else 0
        
        print(f"📱 إرسال تنبيه: {item.get('name', '')[:40]}... - {validation_reason}")
        return True
    else:
        print(f"🚫 تم رفض التنبيه: {item.get('name', '')[:40]}... - {validation_reason}")
        return False

def create_smart_telegram_message(item, old_price, new_price, discount_percent, drop_detected):
    """إنشاء رسالة تليجرام ذكية مع معلومات التحقق"""
    
    validation_status = item.get('validation_status', 'غير محقق')
    validation_score = item.get('validation_score', 0)
    
    # تحديد الأيقونة حسب مستوى الثقة
    if validation_score >= 80:
        trust_icon = "🏆"
        trust_text = "عرض موثوق"
    elif validation_score >= 60:
        trust_icon = "⚠️"
        trust_text = "عرض جيد"
    else:
        trust_icon = "🤔"
        trust_text = "راجع بنفسك"
    
    product_name = item.get('name', 'No name')
    url = item.get('url', '')
    section = item.get('section', 'Unknown')
    
    price_strike = f"<s>{int(old_price):,} EGP</s>" if old_price else ""
    price_now = f"<b>{int(new_price):,} EGP</b>"
    price_row = f"💰 {price_strike} → {price_now}" if price_strike else f"💰 {price_now}"
    
    if drop_detected:
        headline = "🚨 <b>Drop!</b> 🚨"
    elif discount_percent >= 60:
        headline = "🔥 <b>HOT DEAL!</b>"
    elif discount_percent >= 40:
        headline = "✨ <b>Good Deal!</b>"
    else:
        headline = "💸 <b>Deal Alert!</b>"

    msg = f"""{headline}

<b>{product_name}</b>

{price_row}
⚡ <b>Discount:</b> <code>{discount_percent:.1f}%</code>
📦 <b>Section:</b> <code>{section}</code>

{trust_icon} <b>Trust Level:</b> {trust_text} ({validation_score}/100)
🔍 <b>Status:</b> {validation_status}

🔗 <a href="{url}">Open Product</a>
"""
    
    return msg

# اختبار النظام
if __name__ == "__main__":
    print("🧠 اختبار نظام التحقق من العروض الذكي")
    print("=" * 50)
    
    # عروض اختبار
    test_deals = [
        # عرض جيد
        {"asin": "B08N5WRWNW", "name": "Echo Dot 4th Gen", "section": "Electronics", "url": "https://amazon.eg/echo"},
        # عرض مشبوه
        {"asin": "B08FAKE123", "name": "iPhone 15 Pro Max Replica", "section": "Electronics", "url": "https://amazon.eg/fake"},
        # عرض متوسط
        {"asin": "B08NORMAL1", "name": "Bluetooth Headphones", "section": "Electronics", "url": "https://amazon.eg/headphones"}
    ]
    
    test_prices = [
        (1200, 899, 25.1),   # عرض جيد
        (5000, 299, 94.0),   # عرض مشبوه
        (800, 640, 20.0)     # عرض متوسط
    ]
    
    for i, (deal, (old_price, new_price, discount)) in enumerate(zip(test_deals, test_prices)):
        print(f"\n🧪 اختبار العرض {i+1}:")
        print(f"   📦 المنتج: {deal['name']}")
        print(f"   💰 السعر: {old_price} → {new_price} ({discount}% OFF)")
        
        should_send, reason = validator.should_send_alert(deal, old_price, new_price, discount)
        
        if should_send:
            print(f"   ✅ {reason}")
        else:
            print(f"   ❌ {reason}")
    
    # طباعة التقرير
    print(validator.generate_validation_report())
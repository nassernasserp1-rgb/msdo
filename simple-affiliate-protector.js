// نظام حماية كوكيز الأفيليت المبسط - يمكن إدراجه مباشرة
// استبدل 'yajnyeg-21' بـ tag الخاص بك
(function() {
    'use strict';
    
    const AFFILIATE_TAG = 'yajnyeg-21'; // ضع الـ tag الخاص بك هنا
    const PROTECTION_HOURS = 24;
    const AMAZON_DOMAIN = 'amazon.eg';
    
    class QuickAffiliateProtector {
        constructor() {
            this.tag = AFFILIATE_TAG;
            this.domain = AMAZON_DOMAIN;
            this.storageKey = `quick_aff_${this.tag}`;
            this.consentKey = `quick_consent_${this.tag}`;
            this.isActive = false;
            this.interval = null;
            
            this.init();
        }
        
        init() {
            // فحص الموافقة السابقة
            if (this.hasConsent()) {
                this.startProtection();
            } else {
                this.requestConsent();
            }
        }
        
        hasConsent() {
            try {
                const consent = localStorage.getItem(this.consentKey);
                if (!consent) return false;
                const data = JSON.parse(consent);
                return data.accepted && Date.now() < data.expires;
            } catch(e) {
                return false;
            }
        }
        
        requestConsent() {
            // إنشاء نافذة موافقة بسيطة
            const modal = document.createElement('div');
            modal.id = 'quickConsentModal';
            modal.innerHTML = `
                <div style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Arial">
                    <div style="background:white;padding:30px;border-radius:15px;max-width:500px;width:90%;text-align:center">
                        <h3 style="margin:0 0 15px 0;color:#333">🍪 موافقة الكوكيز</h3>
                        <p style="margin:0 0 20px 0;color:#666;text-align:right;line-height:1.6">
                            نحتاج حفظ كوكيز الأفيليت لمدة ${PROTECTION_HOURS} ساعة لضمان حصولنا على العمولة من مشترياتك.<br>
                            <strong>لن يتم جمع أي بيانات شخصية.</strong>
                        </p>
                        <div>
                            <button onclick="window.quickAcceptCookies()" style="background:#28a745;color:white;border:none;padding:12px 25px;margin:5px;border-radius:8px;cursor:pointer;font-weight:600">
                                ✅ موافق
                            </button>
                            <button onclick="window.quickDeclineCookies()" style="background:#dc3545;color:white;border:none;padding:12px 25px;margin:5px;border-radius:8px;cursor:pointer;font-weight:600">
                                ❌ لا شكراً
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // إعداد وظائف الموافقة
            window.quickAcceptCookies = () => {
                this.saveConsent(true);
                modal.remove();
                delete window.quickAcceptCookies;
                delete window.quickDeclineCookies;
                this.startProtection();
            };
            
            window.quickDeclineCookies = () => {
                this.saveConsent(false);
                modal.remove();
                delete window.quickAcceptCookies;
                delete window.quickDeclineCookies;
            };
        }
        
        saveConsent(accepted) {
            const data = {
                accepted: accepted,
                timestamp: Date.now(),
                expires: Date.now() + (PROTECTION_HOURS * 60 * 60 * 1000)
            };
            
            try {
                localStorage.setItem(this.consentKey, JSON.stringify(data));
            } catch(e) {
                console.warn('لا يمكن حفظ الموافقة');
            }
        }
        
        startProtection() {
            if (!this.hasConsent()) return;
            
            // حفظ بيانات الأفيليت
            const affiliateData = {
                tag: this.tag,
                domain: this.domain,
                expires: Date.now() + (PROTECTION_HOURS * 60 * 60 * 1000)
            };
            
            try {
                localStorage.setItem(this.storageKey, JSON.stringify(affiliateData));
            } catch(e) {}
            
            // تعيين الكوكيز
            this.setCookie('amazon_affiliate', this.tag);
            
            // بدء المراقبة
            this.startMonitoring();
            
            // إظهار مؤشر الحماية
            this.showIndicator();
            
            this.isActive = true;
            console.log('🛡️ تم تفعيل حماية الأفيليت');
        }
        
        startMonitoring() {
            if (this.interval) clearInterval(this.interval);
            
            this.interval = setInterval(() => {
                // فحص انتهاء الصلاحية
                const stored = localStorage.getItem(this.storageKey);
                if (!stored) return this.stopProtection();
                
                try {
                    const data = JSON.parse(stored);
                    if (Date.now() > data.expires) {
                        return this.stopProtection();
                    }
                } catch(e) {
                    return this.stopProtection();
                }
                
                // فحص الكوكيز وإعادة تعيينها إذا لزم الأمر
                const currentCookie = this.getCookie('amazon_affiliate');
                if (currentCookie !== this.tag) {
                    this.setCookie('amazon_affiliate', this.tag);
                    console.log('🔄 تم استعادة كوكيز الأفيليت');
                }
                
                // تحديث روابط أمازون
                this.updateLinks();
                
            }, 3000); // فحص كل 3 ثوان
        }
        
        updateLinks() {
            try {
                document.querySelectorAll(`a[href*="${this.domain}"]`).forEach(link => {
                    try {
                        const url = new URL(link.href);
                        if (url.hostname.includes('amazon')) {
                            url.searchParams.set('tag', this.tag);
                            link.href = url.toString();
                        }
                    } catch(e) {}
                });
            } catch(e) {}
        }
        
        setCookie(name, value) {
            const expires = new Date();
            expires.setTime(expires.getTime() + (PROTECTION_HOURS * 60 * 60 * 1000));
            document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
        }
        
        getCookie(name) {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [key, value] = cookie.trim().split('=');
                if (key === name) return value;
            }
            return null;
        }
        
        showIndicator() {
            // إزالة أي مؤشر سابق
            const existing = document.getElementById('quickAffIndicator');
            if (existing) existing.remove();
            
            // إنشاء مؤشر جديد
            const indicator = document.createElement('div');
            indicator.id = 'quickAffIndicator';
            indicator.style.cssText = `
                position: fixed; top: 20px; right: 20px; z-index: 999998;
                background: linear-gradient(45deg, #28a745, #20c997);
                color: white; padding: 8px 15px; border-radius: 20px;
                font-size: 12px; font-weight: bold; 
                box-shadow: 0 4px 15px rgba(40,167,69,0.3);
                animation: quickPulse 2s infinite;
                font-family: Arial, sans-serif;
            `;
            indicator.textContent = '🛡️ حماية نشطة';
            document.body.appendChild(indicator);
            
            // إضافة CSS للأنيميشن
            if (!document.getElementById('quickPulseStyle')) {
                const style = document.createElement('style');
                style.id = 'quickPulseStyle';
                style.textContent = `
                    @keyframes quickPulse {
                        0%, 100% { opacity: 1; transform: scale(1); }
                        50% { opacity: 0.8; transform: scale(1.05); }
                    }
                `;
                document.head.appendChild(style);
            }
        }
        
        stopProtection() {
            if (this.interval) {
                clearInterval(this.interval);
                this.interval = null;
            }
            
            // إزالة المؤشر
            const indicator = document.getElementById('quickAffIndicator');
            if (indicator) indicator.remove();
            
            this.isActive = false;
            console.log('⏰ انتهت حماية الأفيليت');
        }
    }
    
    // تفعيل الحماية
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new QuickAffiliateProtector());
    } else {
        new QuickAffiliateProtector();
    }

})();
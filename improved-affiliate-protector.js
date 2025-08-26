// نسخة محسّنة من نظام حماية كوكيز الأفيليت
(function() {
    'use strict';
    
    const config = {
        affiliateTag: 'YOUR_TAG_HERE',
        domain: 'amazon.com',
        duration: 24,
        theme: 'blue'
    };

    class SecureAffiliateProtector {
        constructor(cfg) {
            this.config = cfg;
            this.storageKey = `aff_protection_${cfg.affiliateTag}_${Date.now()}`;
            this.consentKey = `cookie_consent_${cfg.affiliateTag}`;
            this.protectionActive = false;
            this.checkInterval = null;
            this.uniqueId = `affiliate_${Math.random().toString(36).substr(2, 9)}`;
            
            // تجنب التضارب في الأسماء
            this.consentFunctions = {
                accept: `accept_${this.uniqueId}`,
                decline: `decline_${this.uniqueId}`
            };
            
            this.init();
        }

        init() {
            // فحص الموافقة المحفوظة
            if (this.hasValidConsent()) {
                this.restoreFromStorage();
            } else {
                this.showConsentModal();
            }
        }

        hasValidConsent() {
            try {
                const consent = localStorage.getItem(this.consentKey);
                if (!consent) return false;
                const data = JSON.parse(consent);
                return data.accepted && Date.now() < data.expires;
            } catch(e) {
                console.warn('خطأ في قراءة بيانات الموافقة:', e);
                return false;
            }
        }

        showConsentModal() {
            // التأكد من عدم وجود modal سابق
            const existingModal = document.getElementById(this.uniqueId);
            if (existingModal) {
                existingModal.remove();
            }

            const modalHTML = `
                <div id="${this.uniqueId}" style="
                    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0,0,0,0.8); z-index: 999999;
                    display: flex; align-items: center; justify-content: center;
                    backdrop-filter: blur(5px); font-family: Arial, sans-serif;
                ">
                    <div style="
                        background: white; border-radius: 15px; padding: 30px;
                        max-width: 500px; width: 90%; text-align: center;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
                        animation: slideIn 0.3s ease-out;
                    ">
                        <h2 style="margin: 0 0 15px 0; color: #333;">🍪 موافقة الكوكيز</h2>
                        <p style="margin: 0 0 20px 0; line-height: 1.6; color: #555; text-align: right;">
                            نريد حفظ كوكيز الأفيليت لمدة ${this.config.duration} ساعة لضمان حصولنا على العمولة.<br>
                            <strong>لن يتم جمع أي بيانات شخصية وستبقى الكوكيز محمية من التغيير.</strong>
                        </p>
                        <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                            <button id="${this.consentFunctions.accept}" style="
                                background: linear-gradient(45deg, #48bb78, #38a169); color: white;
                                border: none; padding: 12px 25px; border-radius: 8px;
                                font-weight: 600; cursor: pointer; min-width: 120px;
                                transition: transform 0.2s ease;
                            ">
                                ✅ موافق
                            </button>
                            <button id="${this.consentFunctions.decline}" style="
                                background: linear-gradient(45deg, #f56565, #e53e3e); color: white;
                                border: none; padding: 12px 25px; border-radius: 8px;
                                font-weight: 600; cursor: pointer; min-width: 120px;
                                transition: transform 0.2s ease;
                            ">
                                ❌ لا شكراً
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // إضافة CSS للأنيميشن
            if (!document.getElementById('affiliate-animations')) {
                const style = document.createElement('style');
                style.id = 'affiliate-animations';
                style.textContent = `
                    @keyframes slideIn {
                        from { transform: translateY(-50px); opacity: 0; }
                        to { transform: translateY(0); opacity: 1; }
                    }
                `;
                document.head.appendChild(style);
            }

            // ربط الأحداث بطريقة آمنة
            document.getElementById(this.consentFunctions.accept).addEventListener('click', () => {
                this.handleConsent(true);
            });

            document.getElementById(this.consentFunctions.decline).addEventListener('click', () => {
                this.handleConsent(false);
            });
        }

        handleConsent(accepted) {
            this.saveConsent(accepted);
            const modal = document.getElementById(this.uniqueId);
            if (modal) {
                modal.remove();
            }
            
            if (accepted) {
                this.activateProtection();
            }
        }

        saveConsent(accepted) {
            const consentData = {
                accepted: accepted,
                timestamp: Date.now(),
                expires: Date.now() + (this.config.duration * 60 * 60 * 1000)
            };
            
            try {
                localStorage.setItem(this.consentKey, JSON.stringify(consentData));
            } catch(e) {
                console.warn('لا يمكن حفظ بيانات الموافقة:', e);
            }
        }

        activateProtection() {
            if (!this.hasValidConsent()) {
                console.warn('لا توجد موافقة صالحة');
                return false;
            }

            const affiliateData = {
                tag: this.config.affiliateTag,
                domain: this.config.domain,
                timestamp: Date.now(),
                expires: Date.now() + (this.config.duration * 60 * 60 * 1000)
            };

            // حفظ البيانات بشكل آمن
            try {
                localStorage.setItem(this.storageKey, JSON.stringify(affiliateData));
                this.setCookie('amazon_affiliate', this.config.affiliateTag, this.config.duration);
            } catch(e) {
                console.warn('خطأ في حفظ البيانات:', e);
                return false;
            }
            
            // بدء المراقبة
            this.startProtectionMonitoring(affiliateData);
            this.showProtectionIndicator();
            
            console.log('🛡️ تم تفعيل حماية الأفيليت لمدة ' + this.config.duration + ' ساعة');
            return true;
        }

        startProtectionMonitoring(affiliateData) {
            // تنظيف أي مراقبة سابقة
            if (this.checkInterval) {
                clearInterval(this.checkInterval);
            }

            this.checkInterval = setInterval(() => {
                // فحص انتهاء المدة
                if (Date.now() > affiliateData.expires) {
                    this.stopProtection();
                    return;
                }

                // فحص وإعادة تعيين الكوكيز إذا تغيرت
                const currentCookie = this.getCookie('amazon_affiliate');
                if (currentCookie !== this.config.affiliateTag) {
                    const remainingHours = Math.ceil((affiliateData.expires - Date.now()) / (60 * 60 * 1000));
                    this.setCookie('amazon_affiliate', this.config.affiliateTag, remainingHours);
                    console.log('🔄 تم استعادة كوكيز الأفيليت');
                }

                // تحديث روابط أمازون في الصفحة
                this.updateAmazonLinks();
            }, 5000); // فحص كل 5 ثوان (أقل استهلاكاً للموارد)

            this.protectionActive = true;
        }

        updateAmazonLinks() {
            try {
                const links = document.querySelectorAll(`a[href*="${this.config.domain}"]`);
                links.forEach(link => {
                    try {
                        const url = new URL(link.href);
                        
                        // التأكد من أنه رابط أمازون صحيح
                        if (url.hostname.includes('amazon')) {
                            const currentTag = url.searchParams.get('tag');
                            if (!currentTag || currentTag !== this.config.affiliateTag) {
                                url.searchParams.set('tag', this.config.affiliateTag);
                                url.searchParams.set('linkCode', 'as2');
                                link.href = url.toString();
                            }
                        }
                    } catch(urlError) {
                        // تجاهل الروابط غير الصحيحة
                    }
                });
            } catch(e) {
                console.warn('خطأ في تحديث الروابط:', e);
            }
        }

        showProtectionIndicator() {
            // إزالة أي مؤشر سابق
            const existingIndicator = document.getElementById(`indicator_${this.uniqueId}`);
            if (existingIndicator) {
                existingIndicator.remove();
            }

            const indicator = document.createElement('div');
            indicator.id = `indicator_${this.uniqueId}`;
            indicator.style.cssText = `
                position: fixed; top: 20px; right: 20px; z-index: 999998;
                background: linear-gradient(45deg, #48bb78, #38a169);
                color: white; padding: 8px 15px; border-radius: 20px;
                font-size: 12px; font-weight: bold; box-shadow: 0 4px 15px rgba(72,187,120,0.3);
                animation: pulse 2s infinite; font-family: Arial, sans-serif;
                pointer-events: none;
            `;
            indicator.textContent = '🛡️ الحماية نشطة';
            document.body.appendChild(indicator);

            // إضافة CSS للنبض
            if (!document.getElementById('pulse-animation')) {
                const pulseStyle = document.createElement('style');
                pulseStyle.id = 'pulse-animation';
                pulseStyle.textContent = `
                    @keyframes pulse {
                        0%, 100% { opacity: 1; transform: scale(1); }
                        50% { opacity: 0.8; transform: scale(1.05); }
                    }
                `;
                document.head.appendChild(pulseStyle);
            }
        }

        stopProtection() {
            // تنظيف الفواصل الزمنية
            if (this.checkInterval) {
                clearInterval(this.checkInterval);
                this.checkInterval = null;
            }
            
            // إزالة المؤشر
            const indicator = document.getElementById(`indicator_${this.uniqueId}`);
            if (indicator) {
                indicator.remove();
            }
            
            // تنظيف البيانات المنتهية الصلاحية
            try {
                const stored = localStorage.getItem(this.storageKey);
                if (stored) {
                    const data = JSON.parse(stored);
                    if (Date.now() > data.expires) {
                        localStorage.removeItem(this.storageKey);
                    }
                }
            } catch(e) {
                console.warn('خطأ في تنظيف البيانات:', e);
            }
            
            this.protectionActive = false;
            console.log('⏰ انتهت مدة حماية الأفيليت');
        }

        restoreFromStorage() {
            try {
                const stored = localStorage.getItem(this.storageKey);
                if (!stored) return false;

                const data = JSON.parse(stored);
                if (Date.now() < data.expires) {
                    // إعادة تفعيل الحماية
                    const remainingHours = Math.ceil((data.expires - Date.now()) / (60 * 60 * 1000));
                    this.setCookie('amazon_affiliate', data.tag, remainingHours);
                    this.startProtectionMonitoring(data);
                    this.showProtectionIndicator();
                    return true;
                }
            } catch(e) {
                console.warn('خطأ في استعادة البيانات:', e);
            }
            return false;
        }

        setCookie(name, value, hours) {
            try {
                const expires = new Date();
                expires.setTime(expires.getTime() + (hours * 60 * 60 * 1000));
                document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires.toUTCString()}; path=/; SameSite=Lax; Secure`;
            } catch(e) {
                console.warn('خطأ في حفظ الكوكيز:', e);
            }
        }

        getCookie(name) {
            try {
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const [key, value] = cookie.trim().split('=');
                    if (key === name) {
                        return decodeURIComponent(value);
                    }
                }
            } catch(e) {
                console.warn('خطأ في قراءة الكوكيز:', e);
            }
            return null;
        }

        // تنظيف الموارد عند إزالة الكائن
        destroy() {
            this.stopProtection();
            
            // إزالة أي عناصر DOM مضافة
            const modal = document.getElementById(this.uniqueId);
            if (modal) modal.remove();
            
            const indicator = document.getElementById(`indicator_${this.uniqueId}`);
            if (indicator) indicator.remove();
        }
    }

    // تفعيل النظام مع التعامل مع الأخطاء
    try {
        const protector = new SecureAffiliateProtector(config);
        
        // حفظ مرجع للتنظيف لاحقاً
        window.affiliateProtector = protector;
        
        // تنظيف عند إغلاق الصفحة
        window.addEventListener('beforeunload', () => {
            if (window.affiliateProtector) {
                window.affiliateProtector.destroy();
            }
        });
        
    } catch(e) {
        console.error('خطأ في تشغيل نظام حماية الأفيليت:', e);
    }

})();
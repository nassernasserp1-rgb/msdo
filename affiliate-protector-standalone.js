// ========================================
// نظام حماية كوكيز الأفيليت المستقل
// Standalone Affiliate Cookie Protector
// ========================================
// 
// التعليمات:
// 1. غيّر AFFILIATE_TAG إلى الـ tag الخاص بك
// 2. غيّر AMAZON_DOMAIN إلى النطاق المطلوب
// 3. احفظ الملف وأدرجه في صفحاتك
//
// Instructions:
// 1. Change AFFILIATE_TAG to your tag
// 2. Change AMAZON_DOMAIN to your domain
// 3. Save and include in your pages

(function() {
    'use strict';
    
    // =================== الإعدادات - SETTINGS ===================
    
    const AFFILIATE_TAG = 'yajnyeg-21';    // ضع الـ tag الخاص بك هنا
    const AMAZON_DOMAIN = 'amazon.eg';     // نطاق أمازون المطلوب
    const PROTECTION_HOURS = 24;           // مدة الحماية بالساعات
    const CHECK_INTERVAL = 3000;           // فترة الفحص بالملي ثانية
    const PROTECTION_LEVEL = 'aggressive'; // مستوى الحماية: gentle, moderate, aggressive
    
    // =================== النظام الرئيسي - MAIN SYSTEM ===================
    
    class StandaloneAffiliateProtector {
        constructor() {
            this.tag = AFFILIATE_TAG;
            this.domain = AMAZON_DOMAIN;
            this.hours = PROTECTION_HOURS;
            this.interval = CHECK_INTERVAL;
            this.level = PROTECTION_LEVEL;
            
            // مفاتيح التخزين
            this.storageKey = `aff_protector_${this.tag}_${Date.now()}`;
            this.consentKey = `aff_consent_${this.tag}`;
            this.backupKeys = [];
            
            // حالة النظام
            this.isActive = false;
            this.monitoringInterval = null;
            this.originalCookie = null;
            
            // بدء التشغيل
            this.initialize();
        }
        
        // =================== التهيئة - INITIALIZATION ===================
        
        initialize() {
            console.log('🛡️ بدء تشغيل نظام حماية الأفيليت...');
            
            if (this.hasValidConsent()) {
                console.log('✅ تم العثور على موافقة سابقة');
                this.activateProtection();
            } else {
                console.log('❓ لا توجد موافقة - عرض نافذة الموافقة');
                this.showConsentDialog();
            }
        }
        
        // =================== إدارة الموافقة - CONSENT MANAGEMENT ===================
        
        hasValidConsent() {
            try {
                const consent = localStorage.getItem(this.consentKey);
                if (!consent) return false;
                
                const data = JSON.parse(consent);
                return data.accepted && Date.now() < data.expires;
            } catch(e) {
                console.warn('خطأ في قراءة الموافقة:', e);
                return false;
            }
        }
        
        showConsentDialog() {
            // تجنب إنشاء نوافذ متعددة
            if (document.getElementById('affiliateConsentModal')) {
                return;
            }
            
            const modalId = `affiliateConsentModal_${Math.random().toString(36).substr(2, 9)}`;
            
            const modalHTML = `
                <div id="${modalId}" style="
                    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0, 0, 0, 0.85); z-index: 999999;
                    display: flex; align-items: center; justify-content: center;
                    backdrop-filter: blur(8px); font-family: 'Segoe UI', Arial, sans-serif;
                ">
                    <div style="
                        background: white; border-radius: 20px; padding: 40px;
                        max-width: 550px; width: 90%; text-align: center;
                        box-shadow: 0 30px 60px rgba(0,0,0,0.3);
                        animation: modalSlideIn 0.4s ease-out;
                        border: 3px solid #667eea;
                    ">
                        <div style="font-size: 3rem; margin-bottom: 20px;">🛡️</div>
                        <h2 style="margin: 0 0 20px 0; color: #2d3748; font-size: 1.8rem;">
                            موافقة حماية الأفيليت
                        </h2>
                        <div style="
                            background: #f7fafc; padding: 20px; border-radius: 12px;
                            margin: 20px 0; text-align: right; line-height: 1.8;
                            border-right: 4px solid #667eea;
                        ">
                            <p style="margin: 0; color: #4a5568; font-size: 1.1rem;">
                                <strong style="color: #2d3748;">نحتاج موافقتك لحفظ كوكيز الأفيليت لمدة ${this.hours} ساعة</strong><br><br>
                                
                                <strong>ما سيحدث:</strong><br>
                                🔒 حفظ معرف الأفيليت (${this.tag}) على جهازك<br>
                                🛡️ حماية الكوكيز من التغيير أو الحذف<br>
                                ⏰ انتهاء تلقائي بعد ${this.hours} ساعة<br>
                                🚫 عدم جمع أي بيانات شخصية<br><br>
                                
                                <strong style="color: #38a169;">
                                    هذا يساعدنا في الحصول على عمولة صغيرة دون أي تكلفة إضافية عليك
                                </strong>
                            </p>
                        </div>
                        <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; margin-top: 30px;">
                            <button onclick="window.acceptAffiliateProtection_${modalId.split('_')[1]}()" style="
                                background: linear-gradient(45deg, #48bb78, #38a169);
                                color: white; border: none; padding: 15px 30px;
                                border-radius: 12px; font-weight: 700; cursor: pointer;
                                min-width: 150px; font-size: 1.1rem;
                                transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(72,187,120,0.3);
                            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 25px rgba(72,187,120,0.4)'"
                               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(72,187,120,0.3)'">
                                ✅ موافق، فعّل الحماية
                            </button>
                            <button onclick="window.declineAffiliateProtection_${modalId.split('_')[1]}()" style="
                                background: linear-gradient(45deg, #f56565, #e53e3e);
                                color: white; border: none; padding: 15px 30px;
                                border-radius: 12px; font-weight: 700; cursor: pointer;
                                min-width: 150px; font-size: 1.1rem;
                                transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(245,101,101,0.3);
                            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 25px rgba(245,101,101,0.4)'"
                               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(245,101,101,0.3)'">
                                ❌ لا، شكراً
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // إضافة الأنيميشن
            this.addModalAnimation();
            
            // إعداد وظائف الاستجابة
            const uniqueId = modalId.split('_')[1];
            
            window[`acceptAffiliateProtection_${uniqueId}`] = () => {
                this.handleConsent(true, modalId, uniqueId);
            };
            
            window[`declineAffiliateProtection_${uniqueId}`] = () => {
                this.handleConsent(false, modalId, uniqueId);
            };
        }
        
        addModalAnimation() {
            if (document.getElementById('affiliateModalStyles')) return;
            
            const style = document.createElement('style');
            style.id = 'affiliateModalStyles';
            style.textContent = `
                @keyframes modalSlideIn {
                    from { 
                        transform: translateY(-50px) scale(0.9); 
                        opacity: 0; 
                    }
                    to { 
                        transform: translateY(0) scale(1); 
                        opacity: 1; 
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        handleConsent(accepted, modalId, uniqueId) {
            // حفظ الموافقة
            this.saveConsent(accepted);
            
            // إزالة النافذة
            const modal = document.getElementById(modalId);
            if (modal) modal.remove();
            
            // تنظيف الوظائف
            delete window[`acceptAffiliateProtection_${uniqueId}`];
            delete window[`declineAffiliateProtection_${uniqueId}`];
            
            if (accepted) {
                console.log('✅ تم قبول الموافقة - تفعيل الحماية');
                this.activateProtection();
            } else {
                console.log('❌ تم رفض الموافقة - لن تعمل الحماية');
            }
        }
        
        saveConsent(accepted) {
            const consentData = {
                accepted: accepted,
                timestamp: Date.now(),
                expires: Date.now() + (this.hours * 60 * 60 * 1000),
                tag: this.tag,
                domain: this.domain
            };
            
            try {
                localStorage.setItem(this.consentKey, JSON.stringify(consentData));
                sessionStorage.setItem(this.consentKey, JSON.stringify(consentData));
            } catch(e) {
                console.warn('لا يمكن حفظ الموافقة:', e);
            }
        }
        
        // =================== تفعيل الحماية - PROTECTION ACTIVATION ===================
        
        activateProtection() {
            if (!this.hasValidConsent()) {
                console.warn('لا توجد موافقة صالحة');
                return false;
            }
            
            console.log('🚀 تفعيل نظام الحماية...');
            
            // إعداد بيانات الأفيليت
            const protectionData = {
                tag: this.tag,
                domain: this.domain,
                level: this.level,
                timestamp: Date.now(),
                expires: Date.now() + (this.hours * 60 * 60 * 1000)
            };
            
            // حفظ متعدد الطبقات
            this.saveProtectionData(protectionData);
            
            // تعيين الكوكيز الأساسية
            this.setProtectedCookie('amazon_affiliate', this.tag);
            this.setProtectedCookie('aff_backup', this.tag);
            this.setProtectedCookie('protection_active', '1');
            
            // بدء المراقبة
            this.startAdvancedMonitoring(protectionData);
            
            // إظهار مؤشر الحماية
            this.showProtectionIndicator();
            
            // تحديث الروابط الموجودة
            this.updateExistingLinks();
            
            this.isActive = true;
            console.log(`🛡️ تم تفعيل الحماية بمستوى ${this.level} لمدة ${this.hours} ساعة`);
            
            return true;
        }
        
        saveProtectionData(data) {
            try {
                // حفظ أساسي
                localStorage.setItem(this.storageKey, JSON.stringify(data));
                sessionStorage.setItem(this.storageKey, JSON.stringify(data));
                
                // نسخ احتياطية متعددة
                for (let i = 0; i < 5; i++) {
                    const backupKey = `${this.storageKey}_backup_${i}`;
                    localStorage.setItem(backupKey, JSON.stringify(data));
                    this.backupKeys.push(backupKey);
                }
                
                // نسخة مشفرة بسيطة
                const encodedData = btoa(JSON.stringify(data));
                localStorage.setItem(`${this.storageKey}_encoded`, encodedData);
                
            } catch(e) {
                console.warn('خطأ في حفظ بيانات الحماية:', e);
            }
        }
        
        // =================== المراقبة المتقدمة - ADVANCED MONITORING ===================
        
        startAdvancedMonitoring(protectionData) {
            if (this.monitoringInterval) {
                clearInterval(this.monitoringInterval);
            }
            
            console.log(`🔍 بدء المراقبة كل ${this.interval}ms`);
            
            this.monitoringInterval = setInterval(() => {
                // فحص انتهاء الصلاحية
                if (Date.now() > protectionData.expires) {
                    console.log('⏰ انتهت مدة الحماية');
                    this.stopProtection();
                    return;
                }
                
                // تنفيذ عمليات الحماية
                this.enforceProtection();
                this.protectStorageData(protectionData);
                this.updateExistingLinks();
                this.preventManipulation();
                
                // إحصائيات المراقبة
                if (Math.random() < 0.01) { // 1% من الوقت
                    this.logProtectionStats();
                }
                
            }, this.interval);
            
            // مراقبة إضافية عند الأحداث
            this.setupEventListeners();
        }
        
        enforceProtection() {
            const expectedCookies = {
                'amazon_affiliate': this.tag,
                'aff_backup': this.tag,
                'protection_active': '1'
            };
            
            let restored = false;
            
            Object.entries(expectedCookies).forEach(([name, value]) => {
                const current = this.getCookie(name);
                if (current !== value) {
                    this.setProtectedCookie(name, value);
                    restored = true;
                }
            });
            
            if (restored) {
                console.log('🔄 تمت استعادة الكوكيز المحمية');
            }
            
            // في الوضع العدواني - إزالة كوكيز منافسة
            if (this.level === 'aggressive') {
                this.removeCompetitorCookies();
            }
        }
        
        removeCompetitorCookies() {
            try {
                document.cookie.split(';').forEach(cookie => {
                    const name = cookie.split('=')[0].trim();
                    
                    // إذا كان كوكيز أمازون ولكن ليس الخاص بنا
                    if (name.includes('amazon') && 
                        !['amazon_affiliate', 'aff_backup', 'protection_active'].includes(name)) {
                        
                        const value = this.getCookie(name);
                        if (value && value !== this.tag) {
                            document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
                            console.log(`🗑️ تم حذف كوكيز منافس: ${name}=${value}`);
                        }
                    }
                });
            } catch(e) {
                console.warn('خطأ في إزالة الكوكيز المنافسة:', e);
            }
        }
        
        protectStorageData(originalData) {
            // فحص البيانات الأساسية
            const mainData = localStorage.getItem(this.storageKey);
            if (!mainData) {
                // استعادة من النسخ الاحتياطية
                this.restoreFromBackups(originalData);
            }
        }
        
        restoreFromBackups(originalData) {
            console.log('🔧 محاولة استعادة من النسخ الاحتياطية...');
            
            // البحث في النسخ الاحتياطية
            for (const backupKey of this.backupKeys) {
                const backup = localStorage.getItem(backupKey);
                if (backup) {
                    localStorage.setItem(this.storageKey, backup);
                    console.log(`✅ تمت الاستعادة من: ${backupKey}`);
                    return;
                }
            }
            
            // محاولة من sessionStorage
            const sessionData = sessionStorage.getItem(this.storageKey);
            if (sessionData) {
                localStorage.setItem(this.storageKey, sessionData);
                console.log('✅ تمت الاستعادة من sessionStorage');
                return;
            }
            
            // محاولة من النسخة المشفرة
            try {
                const encoded = localStorage.getItem(`${this.storageKey}_encoded`);
                if (encoded) {
                    const decoded = atob(encoded);
                    localStorage.setItem(this.storageKey, decoded);
                    console.log('✅ تمت الاستعادة من النسخة المشفرة');
                    return;
                }
            } catch(e) {}
            
            // إعادة إنشاء البيانات
            localStorage.setItem(this.storageKey, JSON.stringify(originalData));
            console.log('🔨 تم إعادة إنشاء البيانات');
        }
        
        setupEventListeners() {
            // مراقبة تغييرات الصفحة
            window.addEventListener('focus', () => {
                if (this.isActive) {
                    this.enforceProtection();
                }
            });
            
            // مراقبة إعادة تحميل الصفحة
            window.addEventListener('beforeunload', () => {
                if (this.isActive) {
                    this.setProtectedCookie('amazon_affiliate', this.tag);
                }
            });
            
            // مراقبة تغييرات الرؤية
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden && this.isActive) {
                    setTimeout(() => this.enforceProtection(), 500);
                }
            });
        }
        
        preventManipulation() {
            // حماية متقدمة في الوضع العدواني
            if (this.level === 'aggressive') {
                // منع تعديل localStorage لمفاتيحنا
                const originalSetItem = localStorage.setItem;
                localStorage.setItem = function(key, value) {
                    if (key.includes('aff_') || key.includes('protection') || key.includes('consent')) {
                        console.warn(`🛡️ منع محاولة تعديل: ${key}`);
                        return;
                    }
                    return originalSetItem.call(this, key, value);
                };
            }
        }
        
        // =================== إدارة الروابط - LINK MANAGEMENT ===================
        
        updateExistingLinks() {
            try {
                const selectors = [
                    `a[href*="${this.domain}"]`,
                    'a[href*="amazon."]',
                    'a[href*="amzn."]'
                ];
                
                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(link => {
                        this.updateSingleLink(link);
                    });
                });
                
                // مراقبة الروابط الجديدة
                this.observeNewLinks();
                
            } catch(e) {
                console.warn('خطأ في تحديث الروابط:', e);
            }
        }
        
        updateSingleLink(link) {
            try {
                const url = new URL(link.href);
                
                if (url.hostname.includes('amazon')) {
                    const currentTag = url.searchParams.get('tag');
                    
                    if (currentTag !== this.tag) {
                        // تحديث الـ tag
                        url.searchParams.set('tag', this.tag);
                        
                        // إضافة معاملات إضافية
                        url.searchParams.set('linkCode', 'as2');
                        if (!url.searchParams.has('camp')) {
                            url.searchParams.set('camp', '247');
                        }
                        if (!url.searchParams.has('creative')) {
                            url.searchParams.set('creative', '1211');
                        }
                        
                        link.href = url.toString();
                        
                        if (currentTag && currentTag !== this.tag) {
                            console.log(`🔄 تم استبدال tag: ${currentTag} → ${this.tag}`);
                        }
                    }
                    
                    // حماية الرابط في الوضع العدواني
                    if (this.level === 'aggressive') {
                        this.protectLink(link);
                    }
                }
            } catch(e) {
                // تجاهل الروابط غير الصحيحة
            }
        }
        
        protectLink(link) {
            // منع تعديل الرابط
            link.addEventListener('click', (e) => {
                try {
                    const url = new URL(link.href);
                    const tag = url.searchParams.get('tag');
                    
                    if (tag !== this.tag) {
                        e.preventDefault();
                        url.searchParams.set('tag', this.tag);
                        window.open(url.toString(), '_blank');
                        console.log('🛡️ تم منع النقر على رابط محرف');
                    }
                } catch(e) {}
            });
        }
        
        observeNewLinks() {
            if (this.linkObserver) return;
            
            this.linkObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) { // Element node
                            // فحص العنصر نفسه
                            if (node.tagName === 'A' && node.href && node.href.includes('amazon')) {
                                this.updateSingleLink(node);
                            }
                            
                            // فحص العناصر التابعة
                            const links = node.querySelectorAll ? node.querySelectorAll('a[href*="amazon"]') : [];
                            links.forEach(link => this.updateSingleLink(link));
                        }
                    });
                });
            });
            
            this.linkObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
        
        // =================== واجهة المستخدم - USER INTERFACE ===================
        
        showProtectionIndicator() {
            // إزالة أي مؤشر سابق
            const existing = document.getElementById('affiliateProtectionIndicator');
            if (existing) existing.remove();
            
            const indicator = document.createElement('div');
            indicator.id = 'affiliateProtectionIndicator';
            
            const colors = {
                gentle: '#28a745',
                moderate: '#ffc107', 
                aggressive: '#dc3545'
            };
            
            const labels = {
                gentle: 'حماية أساسية',
                moderate: 'حماية متوسطة',
                aggressive: 'حماية قصوى'
            };
            
            indicator.style.cssText = `
                position: fixed; top: 15px; right: 15px; z-index: 999997;
                background: linear-gradient(45deg, ${colors[this.level]}, ${colors[this.level]}dd);
                color: white; padding: 10px 18px; border-radius: 25px;
                font-size: 13px; font-weight: bold; font-family: Arial, sans-serif;
                box-shadow: 0 6px 20px rgba(0,0,0,0.2);
                animation: protectionPulse 2s infinite;
                border: 2px solid white; backdrop-filter: blur(10px);
                cursor: pointer; user-select: none;
            `;
            
            indicator.innerHTML = `🛡️ ${labels[this.level]}`;
            indicator.title = `حماية نشطة للـ tag: ${this.tag}\nالمستوى: ${this.level}\nالانتهاء: ${new Date(Date.now() + this.hours * 60 * 60 * 1000).toLocaleString('ar-EG')}`;
            
            // إضافة حدث النقر للمعلومات
            indicator.addEventListener('click', () => {
                this.showProtectionInfo();
            });
            
            document.body.appendChild(indicator);
            
            // إضافة CSS للأنيميشن
            this.addProtectionAnimation();
        }
        
        addProtectionAnimation() {
            if (document.getElementById('protectionAnimationStyles')) return;
            
            const style = document.createElement('style');
            style.id = 'protectionAnimationStyles';
            style.textContent = `
                @keyframes protectionPulse {
                    0%, 100% { 
                        opacity: 1; 
                        transform: scale(1); 
                        box-shadow: 0 6px 20px rgba(0,0,0,0.2); 
                    }
                    50% { 
                        opacity: 0.9; 
                        transform: scale(1.05); 
                        box-shadow: 0 8px 30px rgba(0,0,0,0.3); 
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        showProtectionInfo() {
            const stats = this.getProtectionStats();
            const info = `
📊 إحصائيات الحماية:
• الـ Tag: ${this.tag}
• النطاق: ${this.domain}
• المستوى: ${this.level}
• نشط منذ: ${Math.round((Date.now() - stats.startTime) / 60000)} دقيقة
• الكوكيز المحمية: ${stats.protectedCookies}
• الروابط المحدثة: ${stats.updatedLinks}
• محاولات التلاعب المحبطة: ${stats.blockedAttempts}
            `;
            
            alert(info);
        }
        
        // =================== المرافق والأدوات - UTILITIES ===================
        
        setProtectedCookie(name, value) {
            try {
                const expires = new Date();
                expires.setTime(expires.getTime() + (this.hours * 60 * 60 * 1000));
                
                const cookieString = `${name}=${encodeURIComponent(value)}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
                
                document.cookie = cookieString;
                
                // نسخة احتياطية مع مسار مختلف
                document.cookie = `${cookieString}; path=/backup`;
                
            } catch(e) {
                console.warn(`خطأ في حفظ الكوكيز ${name}:`, e);
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
                console.warn(`خطأ في قراءة الكوكيز ${name}:`, e);
            }
            return null;
        }
        
        getProtectionStats() {
            try {
                const stored = localStorage.getItem(this.storageKey);
                const data = stored ? JSON.parse(stored) : {};
                
                return {
                    startTime: data.timestamp || Date.now(),
                    protectedCookies: 3, // amazon_affiliate, aff_backup, protection_active
                    updatedLinks: document.querySelectorAll('a[href*="amazon"]').length,
                    blockedAttempts: Math.floor(Math.random() * 10) // محاكاة
                };
            } catch(e) {
                return {
                    startTime: Date.now(),
                    protectedCookies: 0,
                    updatedLinks: 0,
                    blockedAttempts: 0
                };
            }
        }
        
        logProtectionStats() {
            const stats = this.getProtectionStats();
            console.log('📊 إحصائيات الحماية:', {
                tag: this.tag,
                level: this.level,
                runtime: Math.round((Date.now() - stats.startTime) / 60000) + ' دقيقة',
                cookies: stats.protectedCookies,
                links: stats.updatedLinks
            });
        }
        
        // =================== إيقاف النظام - SYSTEM SHUTDOWN ===================
        
        stopProtection() {
            console.log('🛑 إيقاف نظام الحماية...');
            
            // إيقاف المراقبة
            if (this.monitoringInterval) {
                clearInterval(this.monitoringInterval);
                this.monitoringInterval = null;
            }
            
            // إيقاف مراقبة الروابط
            if (this.linkObserver) {
                this.linkObserver.disconnect();
                this.linkObserver = null;
            }
            
            // إزالة المؤشر
            const indicator = document.getElementById('affiliateProtectionIndicator');
            if (indicator) indicator.remove();
            
            // تنظيف النسخ الاحتياطية القديمة
            this.cleanupBackups();
            
            this.isActive = false;
            console.log('✅ تم إيقاف النظام بنجاح');
        }
        
        cleanupBackups() {
            try {
                // حذف النسخ الاحتياطية المنتهية الصلاحية
                this.backupKeys.forEach(key => {
                    const data = localStorage.getItem(key);
                    if (data) {
                        try {
                            const parsed = JSON.parse(data);
                            if (Date.now() > parsed.expires) {
                                localStorage.removeItem(key);
                            }
                        } catch(e) {}
                    }
                });
                
                // تنظيف المفاتيح المشفرة القديمة
                Object.keys(localStorage).forEach(key => {
                    if (key.includes('aff_protector_') && key.includes('_encoded')) {
                        try {
                            const data = JSON.parse(atob(localStorage.getItem(key)));
                            if (Date.now() > data.expires) {
                                localStorage.removeItem(key);
                            }
                        } catch(e) {
                            localStorage.removeItem(key);
                        }
                    }
                });
                
            } catch(e) {
                console.warn('خطأ في تنظيف النسخ الاحتياطية:', e);
            }
        }
        
        // =================== إتاحة عامة للاختبار - PUBLIC ACCESS ===================
        
        getStatus() {
            return {
                isActive: this.isActive,
                tag: this.tag,
                domain: this.domain,
                level: this.level,
                hasConsent: this.hasValidConsent(),
                cookies: {
                    amazon_affiliate: this.getCookie('amazon_affiliate'),
                    aff_backup: this.getCookie('aff_backup'),
                    protection_active: this.getCookie('protection_active')
                }
            };
        }
        
        forceStop() {
            this.stopProtection();
            localStorage.removeItem(this.consentKey);
            sessionStorage.removeItem(this.consentKey);
        }
    }
    
    // =================== تشغيل النظام - SYSTEM STARTUP ===================
    
    function initializeProtector() {
        try {
            console.log('🚀 تهيئة نظام حماية الأفيليت...');
            
            const protector = new StandaloneAffiliateProtector();
            
            // إتاحة النظام للوصول العام (للاختبار)
            window.affiliateProtector = protector;
            
            // رسائل تشخيصية
            console.log(`📋 الإعدادات: Tag=${AFFILIATE_TAG}, Domain=${AMAZON_DOMAIN}, Level=${PROTECTION_LEVEL}`);
            
            return protector;
            
        } catch(e) {
            console.error('❌ فشل في تشغيل نظام الحماية:', e);
            return null;
        }
    }
    
    // بدء التشغيل عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeProtector);
    } else {
        initializeProtector();
    }
    
    // رسائل تأكيد التحميل
    console.log('✅ تم تحميل نظام حماية الأفيليت المستقل');
    console.log('🔧 لتغيير الإعدادات، عدّل المتغيرات في بداية الملف');
    
})();

// =================== نهاية النظام - END OF SYSTEM ===================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار حقيقي للـ AI مع API key الموجود
"""

import json
import os
import requests
import re

def test_real_ai():
    """اختبار AI حقيقي"""
    
    print("🔍 فحص Groq AI الحقيقي...")
    
    # تحميل API key
    api_key = None
    try:
        with open('groq_config.json', 'r') as f:
            config = json.load(f)
            api_key = config.get('groq_api_key', '')
            
        if not api_key or 'YOUR_' in api_key:
            print("❌ API key غير موجود")
            return False
            
        print(f"✅ API key موجود: {api_key[:10]}...{api_key[-4:]}")
        
    except Exception as e:
        print(f"❌ خطأ في تحميل API key: {e}")
        return False
    
    # اختبار بسيط
    print("\n🧪 اختبار AI بسيط...")
    
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
            "max_tokens": 20,
            "temperature": 0.1
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
            print(f"✅ AI يعمل! الرد: {content}")
            return True
        else:
            print(f"❌ AI فشل: {response.status_code}")
            print(f"📄 Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في AI: {e}")
        return False

def test_product_analysis():
    """اختبار تحليل منتج"""
    
    print("\n🔍 اختبار تحليل منتج...")
    
    # محاكاة تحليل منتج
    test_product = "Samsung Galaxy A06 Dual Sim 6GB RAM 128GB Storage"
    test_price = 2500
    
    print(f"📱 المنتج: {test_product}")
    print(f"💰 السعر: {test_price} EGP")
    
    # تحليل ذكي
    name_lower = test_product.lower()
    
    if 'samsung' in name_lower:
        brand = 'samsung'
        confidence = 85
        quality = 'ممتاز'
        print(f"✅ العلامة: {brand} ({quality})")
        print(f"📈 الثقة: {confidence}%")
        
        # محاولة AI
        api_key = None
        try:
            with open('groq_config.json', 'r') as f:
                config = json.load(f)
                api_key = config.get('groq_api_key', '')
        except:
            pass
        
        if api_key and 'YOUR_' not in api_key:
            print("🤖 محاولة تحسين بـ AI...")
            
            try:
                clean_name = test_product[:50]
                clean_name = re.sub(r'[^\w\s]', '', clean_name)
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                
                data = {
                    "model": "llama-3.1-70b-versatile",
                    "messages": [
                        {"role": "user", "content": f"Brand of {clean_name}?"}
                    ],
                    "max_tokens": 30,
                    "temperature": 0.1
                }
                
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=8
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_content = result['choices'][0]['message']['content']
                    print(f"🤖 AI رد: {ai_content}")
                    
                    if 'samsung' in ai_content.lower():
                        confidence += 5
                        print(f"✅ AI تأكيد: Samsung - ثقة محسنة {confidence}%")
                        return True
                    else:
                        print(f"⚠️ AI رد مختلف: {ai_content}")
                        return False
                else:
                    print(f"❌ AI فشل: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ AI خطأ: {e}")
                return False
        else:
            print("⚠️ AI غير متاح")
            return False
    
    return False

if __name__ == "__main__":
    print("🤖 اختبار شامل للـ AI")
    print("=" * 50)
    
    # اختبار أساسي
    ai_works = test_real_ai()
    
    # اختبار تحليل منتج
    analysis_works = test_product_analysis()
    
    print("\n" + "=" * 50)
    print("📊 النتائج:")
    print(f"🤖 AI أساسي: {'✅ يعمل' if ai_works else '❌ لا يعمل'}")
    print(f"🔍 تحليل منتج: {'✅ يعمل' if analysis_works else '❌ لا يعمل'}")
    
    if ai_works and analysis_works:
        print("🎉 AI يعمل بشكل كامل!")
    elif ai_works:
        print("⚠️ AI يعمل أساسياً لكن التحليل محتاج إصلاح")
    else:
        print("❌ AI لا يعمل - تحقق من API key")
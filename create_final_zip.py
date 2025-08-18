#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إنشاء ملف ZIP كامل للمشروع
"""

import zipfile
import os

def create_project_zip():
    """إنشاء ملف ZIP يحتوي على جميع ملفات المشروع"""
    
    zip_filename = "LAQTA_AI_COMPLETE_FINAL.zip"
    
    # الملفات المطلوبة
    required_files = [
        "laqta_ai_final.py",
        "groq_config.json", 
        "HOW_TO_ADD_API_KEY.md"
    ]
    
    # إنشاء ملف requirements.txt
    requirements_content = """# LAQTA AI System Requirements
customtkinter>=5.2.0
requests>=2.31.0
playwright>=1.40.0
Pillow>=10.0.0
asyncio-throttle>=1.0.2

# Installation:
# pip install -r requirements.txt
# playwright install chromium
"""
    
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements_content)
    
    # إنشاء ملف telegram_config.json template
    telegram_config = {
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "users": ["YOUR_CHAT_ID_HERE"],
        "instructions": {
            "step1": "Create bot via @BotFather on Telegram",
            "step2": "Get bot token and put it in bot_token",
            "step3": "Get your chat ID and put it in users array",
            "step4": "You can add multiple user IDs in the array"
        }
    }
    
    import json
    with open("telegram_config.json", "w", encoding="utf-8") as f:
        json.dump(telegram_config, f, indent=4, ensure_ascii=False)
    
    # إنشاء README سريع
    readme_content = """# 🤖 LAQTA AI - Professional Amazon Scraper

## 🚀 Quick Start:

### 1. Install Requirements:
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure (Optional):
- **For AI**: Edit `groq_config.json` - add your free Groq API key
- **For Telegram**: Edit `telegram_config.json` - add bot token and chat ID

### 3. Run:
```bash
python laqta_ai_final.py
```

## 🎯 Features:
- ✅ **AI-Powered Analysis** (with Groq - free 100k tokens/day)
- ✅ **Real Price Comparison** with Egyptian market (Noon, Kanbkam)
- ✅ **Smart Product Detection** - finds new products automatically
- ✅ **Professional Telegram Alerts** with product images
- ✅ **Works without AI** - smart fallback system

## 🔧 Configuration Files:
- `groq_config.json` - AI settings (optional)
- `telegram_config.json` - Telegram bot settings (optional)

## 📖 Full Setup Guide:
Read `HOW_TO_ADD_API_KEY.md` for detailed instructions.

---
**🏆 Professional Amazon Egypt scraper with AI market analysis!**
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # إضافة الملفات الجديدة للقائمة
    all_files = required_files + [
        "requirements.txt",
        "telegram_config.json", 
        "README.md"
    ]
    
    # إنشاء ZIP
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename in all_files:
            if os.path.exists(filename):
                zipf.write(filename)
                print(f"✅ Added: {filename}")
            else:
                print(f"❌ Missing: {filename}")
    
    # معلومات الملف
    if os.path.exists(zip_filename):
        size = os.path.getsize(zip_filename)
        print(f"\n🎉 ZIP Created Successfully!")
        print(f"📁 File: {zip_filename}")
        print(f"📏 Size: {size:,} bytes ({size/1024:.1f} KB)")
        print(f"📦 Files: {len(all_files)}")
        
        print(f"\n📋 Contents:")
        for filename in all_files:
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"   - {filename} ({file_size:,} bytes)")
        
        return zip_filename
    else:
        print("❌ Failed to create ZIP file")
        return None

if __name__ == "__main__":
    create_project_zip()
#!/usr/bin/env python3
"""
سكريبت لتقسيم ملف JSON الكبير إلى أجزاء صغيرة
مفيد لإرسال ملفات JSON كبيرة عبر الإنترنت
"""

import json
import os
import sys
import argparse
from pathlib import Path

def split_json_file(input_file, output_dir, chunk_size=10000, max_file_size_mb=50):
    """
    تقسيم ملف JSON إلى أجزاء صغيرة
    
    Args:
        input_file (str): مسار ملف JSON المدخل
        output_dir (str): مجلد حفظ الأجزاء
        chunk_size (int): عدد العناصر في كل جزء
        max_file_size_mb (int): الحد الأقصى لحجم الملف بالميجابايت
    """
    
    # التحقق من وجود الملف
    if not os.path.exists(input_file):
        print(f"❌ الملف غير موجود: {input_file}")
        return False
    
    # إنشاء مجلد الإخراج
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 قراءة الملف: {input_file}")
    
    try:
        # قراءة الملف
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # التحقق من نوع البيانات
        if isinstance(data, dict):
            items = list(data.items())
            is_dict = True
        elif isinstance(data, list):
            items = data
            is_dict = False
        else:
            print("❌ نوع البيانات غير مدعوم. يجب أن يكون dict أو list")
            return False
        
        total_items = len(items)
        print(f"📊 إجمالي العناصر: {total_items:,}")
        
        # حساب عدد الأجزاء
        num_chunks = (total_items + chunk_size - 1) // chunk_size
        print(f"🔢 عدد الأجزاء المتوقعة: {num_chunks}")
        
        # تقسيم البيانات
        chunk_num = 1
        for i in range(0, total_items, chunk_size):
            chunk_items = items[i:i + chunk_size]
            
            # إنشاء البيانات للجزء
            if is_dict:
                chunk_data = dict(chunk_items)
            else:
                chunk_data = chunk_items
            
            # اسم ملف الجزء
            base_name = Path(input_file).stem
            chunk_filename = f"{base_name}_part_{chunk_num:03d}.json"
            chunk_path = os.path.join(output_dir, chunk_filename)
            
            # حفظ الجزء
            with open(chunk_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)
            
            # حساب حجم الملف
            file_size = os.path.getsize(chunk_path) / (1024 * 1024)  # MB
            
            print(f"✅ الجزء {chunk_num:03d}: {len(chunk_items):,} عنصر - {file_size:.1f} MB")
            
            # التحقق من حجم الملف
            if file_size > max_file_size_mb:
                print(f"⚠️  تحذير: الجزء {chunk_num} أكبر من {max_file_size_mb} MB")
            
            chunk_num += 1
        
        # إنشاء ملف معلومات
        info_file = os.path.join(output_dir, "split_info.json")
        info_data = {
            "original_file": input_file,
            "total_items": total_items,
            "chunk_size": chunk_size,
            "num_chunks": chunk_num - 1,
            "data_type": "dict" if is_dict else "list",
            "max_file_size_mb": max_file_size_mb
        }
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 تم التقسيم بنجاح!")
        print(f"📁 المجلد: {output_dir}")
        print(f"📄 عدد الأجزاء: {chunk_num - 1}")
        print(f"ℹ️  معلومات التقسيم: {info_file}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ خطأ في قراءة JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False

def combine_json_files(input_dir, output_file):
    """
    دمج الأجزاء مرة أخرى إلى ملف واحد
    
    Args:
        input_dir (str): مجلد الأجزاء
        output_file (str): مسار ملف الإخراج
    """
    
    if not os.path.exists(input_dir):
        print(f"❌ المجلد غير موجود: {input_dir}")
        return False
    
    # قراءة معلومات التقسيم
    info_file = os.path.join(input_dir, "split_info.json")
    if not os.path.exists(info_file):
        print(f"❌ ملف المعلومات غير موجود: {info_file}")
        return False
    
    try:
        with open(info_file, 'r', encoding='utf-8') as f:
            info = json.load(f)
        
        data_type = info.get("data_type", "dict")
        is_dict = data_type == "dict"
        
        print(f"🔄 دمج الأجزاء...")
        print(f"📊 نوع البيانات: {data_type}")
        
        combined_data = {} if is_dict else []
        
        # البحث عن ملفات الأجزاء
        chunk_files = []
        for file in os.listdir(input_dir):
            if file.startswith("amz_products_part_") and file.endswith(".json"):
                chunk_files.append(file)
        
        chunk_files.sort()  # ترتيب الملفات
        
        print(f"📁 عدد ملفات الأجزاء: {len(chunk_files)}")
        
        # دمج الأجزاء
        for chunk_file in chunk_files:
            chunk_path = os.path.join(input_dir, chunk_file)
            print(f"📄 قراءة: {chunk_file}")
            
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            if is_dict:
                combined_data.update(chunk_data)
            else:
                combined_data.extend(chunk_data)
        
        # حفظ الملف المدمج
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        print(f"\n🎉 تم الدمج بنجاح!")
        print(f"📁 الملف: {output_file}")
        print(f"📊 الحجم: {file_size:.1f} MB")
        print(f"🔢 العناصر: {len(combined_data):,}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في الدمج: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="تقسيم ودمج ملفات JSON الكبيرة")
    parser.add_argument("action", choices=["split", "combine"], help="العملية المطلوبة")
    parser.add_argument("input", help="ملف أو مجلد المدخل")
    parser.add_argument("output", help="ملف أو مجلد الإخراج")
    parser.add_argument("--chunk-size", type=int, default=10000, help="عدد العناصر في كل جزء")
    parser.add_argument("--max-size", type=int, default=50, help="الحد الأقصى لحجم الملف بالميجابايت")
    
    args = parser.parse_args()
    
    if args.action == "split":
        success = split_json_file(args.input, args.output, args.chunk_size, args.max_size)
    else:  # combine
        success = combine_json_files(args.input, args.output)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    # مثال على الاستخدام
    if len(sys.argv) == 1:
        print("🔧 سكريبت تقسيم ملفات JSON الكبيرة")
        print("\n📋 الاستخدام:")
        print("  تقسيم ملف:")
        print("    python split_json.py split amz_products.json chunks/")
        print("\n  دمج الأجزاء:")
        print("    python split_json.py combine chunks/ amz_products_combined.json")
        print("\n  مع خيارات إضافية:")
        print("    python split_json.py split amz_products.json chunks/ --chunk-size 5000 --max-size 25")
        print("\n💡 نصائح:")
        print("  - استخدم chunk-size=5000 للأجزاء الصغيرة")
        print("  - استخدم max-size=25 لتجنب الملفات الكبيرة جداً")
        print("  - يمكنك إرسال الأجزاء بشكل منفصل")
    else:
        main()
# [file name]: start.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
برنامج تشغيل بوت XMPP العربي
تشغيل: python start.py
"""

import sys
import os

# إضافة المسار الحالي إلى Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# التحقق من وجود المكتبات المطلوبة
try:
    import xmpp
    import sqlite3
    print("✅ جميع المكتبات المطلوبة مثبتة")
except ImportError as e:
    print(f"❌ مكتبة مفقودة: {e}")
    print("📦 قم بتثبيت المتطلبات: pip install -r requirements.txt")
    sys.exit(1)

# التحقق من وجود مجلد plugins
if not os.path.exists("plugins"):
    print("❌ مجلد plugins غير موجود")
    print("📁 يرجى إنشاء مجلد plugins ووضع البلاجنات فيه")
    sys.exit(1)

# تشغيل البوت
from run import main

if __name__ == "__main__":
    main()
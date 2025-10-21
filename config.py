# -*- coding: utf-8 -*-
import os
import sys
import re

# إعدادات البوت الأساسية
BOT_JID = "fatalnew@jabber.ru"  # استبدل بـ JID البوت الحقيقي
BOT_PASSWORD = "pjzfkbsb22"    # استبدل بكلمة مرور البوت
BOT_NICKNAME = "xbot"
BOT_STATUS = "نظام إدارة عربي متكامل"

# قائمة المالكين (يجب أن تكون مطابقة تماماً لما في run.py)
BOT_OWNERS = ["aboabdelmalek@xmpp.ru"]  # ✅ تم التصحيح من OWNER_JIDS إلى BOT_OWNERS

# إعدادات الخادم
SERVER = "jabber.ru"       # استبدل بخادم XMPP الحقيقي
PORT = 5222
USE_TLS = True

# إعدادات قاعدة البيانات
DATABASE_PATH = "data/sqlite.db"

# إعدادات البلاجنات
PLUGINS_DIR = "plugins"
AUTO_JOIN_ROOMS = [
     "syriatalk@conference.jabber.ru"  # غرف الانضمام التلقائي
]

# مستويات التصريح
OWNER_PERMISSION_LEVEL = 10
ROOM_OWNER_LEVEL = 8
ADMIN_LEVEL = 7
MEMBER_LEVEL = 5
DEFAULT_PERMISSION_LEVEL = 1

# ❌ إزالة دالة is_owner من هنا لأنها موجودة في run.py
# [file name]: database.py
# -*- coding: utf-8 -*-

import sqlite3
import os
import re
import codecs
from config import DATABASE_PATH, BOT_OWNERS

def ensure_data_dir():
    """تأكد من وجود مجلد data"""
    if not os.path.exists("data"):
        os.makedirs("data")

def safe_decode_db(text):
    """فك ترميز النص لقاعدة البيانات بأمان"""
    if text is None:
        return ""
    
    if isinstance(text, str):
        return text
    
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return text.decode('utf-8', errors='ignore')
            except:
                return str(text, errors='ignore')
    
    return str(text)

def clean_jid(jid):
    """تنظيف JID من أي إضافات غير ضرورية - الإصدار النهائي"""
    if not jid:
        return ""
    
    # تحويل إلى نص وإزالة المسافات
    jid_str = str(jid).strip()
    
    # تحويل إلى أحرف صغيرة للمقارنة الموحدة
    jid_lower = jid_str.lower()
    
    # إزالة أي مسافات زائدة
    jid_clean = ' '.join(jid_lower.split())
    
    print(f"🔍 clean_jid: '{jid_str}' → '{jid_clean}'")
    
    return jid_clean

def extract_bare_jid(full_jid):
    """استخراج Bare JID من JID الكامل"""
    if not full_jid:
        return ""
    
    jid_str = str(full_jid).strip()
    
    # إذا كان يحتوي على مورد، نأخذ الجزء الأساسي فقط
    if '/' in jid_str:
        bare_jid = jid_str.split('/')[0]
    else:
        bare_jid = jid_str
    
    return clean_jid(bare_jid)

def get_db_connection():
    """الحصول على اتصال بقاعدة البيانات مع دعم Unicode"""
    ensure_data_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    
    # إعداد الاتصال لدعم Unicode
    conn.execute('PRAGMA encoding = "UTF-8"')
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    
    return conn

# مرادف للتوافق مع run.py
def get_connection():
    """مرادف لـ get_db_connection للتوافق"""
    return get_db_connection()

# تحديث دوال قاعدة البيانات لاستخدام safe_decode_db
def db_execute(query, params=()):
    """تنفيذ استعلام INSERT/UPDATE/DELETE مع معالجة الترميز"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # معالجة الباراميترات للتأكد من أنها نصية
        processed_params = []
        for param in params:
            processed_params.append(safe_decode_db(param))
        
        cursor.execute(query, tuple(processed_params))
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        print(f"❌ خطأ في تنفيذ استعلام: {e}")
        print(f"🔍 الاستعلام: {query}")
        print(f"🔍 الباراميترات: {params}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def db_fetchall(query, params=()):
    """تنفيذ استعلام SELECT وإرجاع جميع النتائج مع معالجة الترميز"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # معالجة الباراميترات للتأكد من أنها نصية
        processed_params = []
        for param in params:
            if isinstance(param, bytes):
                processed_params.append(param.decode('utf-8', errors='ignore'))
            else:
                processed_params.append(str(param) if param is not None else None)
        
        cursor.execute(query, tuple(processed_params))
        results = cursor.fetchall()
        
        # تحويل النتائج إلى قاموس مع معالجة الترميز
        decoded_results = []
        for row in results:
            row_dict = {}
            for key in row.keys():
                value = row[key]
                if isinstance(value, bytes):
                    try:
                        row_dict[key] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        row_dict[key] = value.decode('utf-8', errors='ignore')
                else:
                    row_dict[key] = value
            decoded_results.append(row_dict)
            
        return decoded_results
    except Exception as e:
        print(f"❌ خطأ في استعلام قاعدة البيانات: {e}")
        print(f"🔍 الاستعلام: {query}")
        print(f"🔍 الباراميترات: {params}")
        return []
    finally:
        conn.close()

def db_fetchone(query, params=()):
    """تنفيذ استعلام SELECT وإرجاع نتيجة واحدة مع معالجة الترميز"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # معالجة الباراميترات للتأكد من أنها نصية
        processed_params = []
        for param in params:
            if isinstance(param, bytes):
                processed_params.append(param.decode('utf-8', errors='ignore'))
            else:
                processed_params.append(str(param) if param is not None else None)
        
        cursor.execute(query, tuple(processed_params))
        result = cursor.fetchone()
        
        if result:
            # تحويل النتيجة إلى قاموس مع معالجة الترميز
            result_dict = {}
            for key in result.keys():
                value = result[key]
                if isinstance(value, bytes):
                    try:
                        result_dict[key] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        result_dict[key] = value.decode('utf-8', errors='ignore')
                else:
                    result_dict[key] = value
            return result_dict
        
        return None
    except Exception as e:
        print(f"❌ خطأ في استعلام قاعدة البيانات: {e}")
        print(f"🔍 الاستعلام: {query}")
        print(f"🔍 الباراميترات: {params}")
        return None
    finally:
        conn.close()
        
def init_acl_table():
    """تهيئة جدول ACL في قاعدة البيانات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS acl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                action TEXT NOT NULL,
                condition TEXT NOT NULL,
                value TEXT NOT NULL,
                command TEXT,
                level INTEGER DEFAULT 7,
                expiry INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("✅ تم تهيئة جدول ACL بنجاح")
    except Exception as e:
        print(f"❌ خطأ في تهيئة جدول ACL: {e}")
    finally:
        conn.close()

def init_database():
    """تهيئة قاعدة البيانات والجداول المطلوبة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # جدول المالكين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_owner (
                jid TEXT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by TEXT
            )
        ''')
        
        # جدول الغرف
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                room TEXT PRIMARY KEY,
                auto_join BOOLEAN DEFAULT 1,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول مستخدمي الغرف (لتتبع الأسماء السابقة)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS muc_users (
                room TEXT,
                jid TEXT,
                nick TEXT,
                affiliation TEXT,
                role TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (room, jid, nick)
            )
        ''')
        
        # جدول إعدادات البلاجنات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plugin_data (
                plugin TEXT,
                key TEXT,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (plugin, key)
            )
        ''')
        
        # جدول الحظر المؤقت
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tmp_ban (
                room TEXT,
                jid TEXT,
                time INTEGER,
                reason TEXT,
                PRIMARY KEY (room, jid)
            )
        ''')
        
        # جدول الاستثناءات من الحظر العام
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ignore_ban (
                room TEXT PRIMARY KEY
            )
        ''')
        
        # جدول المذكرات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sayto (
                who TEXT,
                room TEXT,
                jid TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول قفل الرسائل الخاصة (مطلوب لبلجن mucfilter)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS muc_lock (
                room TEXT,
                jid TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (room, jid)
            )
        ''')
        
        # جدول التصاريح الإضافية (جديد)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                jid TEXT,
                room TEXT,
                permission_level INTEGER DEFAULT 1,
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                PRIMARY KEY (jid, room)
            )
        ''')
        
        conn.commit()
        print("✅ تم تهيئة قاعدة البيانات بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        conn.rollback()
    finally:
        conn.close()
    
def is_owner(jid):
    """التحقق إذا كان JID معيناً من مالكي البوت - الإصدار المصحح"""
    try:
        if not jid:
            print("❌ JID فارغ في is_owner")
            return False
            
        jid_str = str(jid).strip()
        print(f"🔍 is_owner التحقق من: '{jid_str}'")
        
        # استخراج Bare JID أولاً
        bare_jid = extract_bare_jid(jid_str)
        print(f"🔍 Bare JID المستخرج: '{bare_jid}'")
        
        print(f"📋 المالكين المسجلين: {BOT_OWNERS}")
        
        # المقارنة مع المالكين المسجلين
        for owner in BOT_OWNERS:
            owner_clean = extract_bare_jid(owner)
            print(f"🔍 مقارنة: '{bare_jid}' == '{owner_clean}' → {bare_jid == owner_clean}")
            
            if bare_jid == owner_clean:
                print(f"✅ تم التعرف على المالك: {bare_jid}")
                return True
        
        print(f"❌ ليس مالكاً: {bare_jid}")
        return False
        
    except Exception as e:
        print(f"❌ خطأ في is_owner: {e}")
        import traceback
        traceback.print_exc()
        return False
        
def add_owner(jid, added_by="system"):
    """إضافة مالك جديد"""
    clean_jid_to_add = clean_jid(jid)
    result = db_execute(
        'INSERT OR REPLACE INTO bot_owner (jid, added_by) VALUES (?, ?)',
        (clean_jid_to_add, added_by)
    )
    return result > 0

def remove_owner(jid):
    """إزالة مالك"""
    clean_jid_to_remove = clean_jid(jid)
    result = db_execute('DELETE FROM bot_owner WHERE jid = ?', (clean_jid_to_remove,))
    return result > 0

def list_owners():
    """عرض قائمة المالكين"""
    return db_fetchall('SELECT jid, added_at, added_by FROM bot_owner ORDER BY added_at')

def get_user_permission(jid, room=""):
    """الحصول على مستوى تصريح المستخدم من قاعدة البيانات"""
    clean_user_jid = clean_jid(jid)
    
    # البحث عن تصريح مخصص
    permission = db_fetchone(
        'SELECT permission_level FROM user_permissions WHERE jid = ? AND room = ?',
        (clean_user_jid, room)
    )
    
    if permission:
        return permission['permission_level']
    
    return None

def set_user_permission(jid, room, level, granted_by="system"):
    """تعيين مستوى تصريح للمستخدم"""
    clean_user_jid = clean_jid(jid)
    result = db_execute('''
        INSERT OR REPLACE INTO user_permissions 
        (jid, room, permission_level, granted_by) 
        VALUES (?, ?, ?, ?)
    ''', (clean_user_jid, room, level, granted_by))
    
    return result > 0

def remove_user_permission(jid, room):
    """إزالة تصريح مخصص للمستخدم"""
    clean_user_jid = clean_jid(jid)
    result = db_execute(
        'DELETE FROM user_permissions WHERE jid = ? AND room = ?',
        (clean_user_jid, room)
    )
    return result > 0

# تهيئة قاعدة البيانات تلقائياً عند الاستيراد
init_database()
init_acl_table()
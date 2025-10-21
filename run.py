# -*- coding: utf-8 -*-

import xmpp
import time
import threading
import re
import sys
import codecs
from config import *
from database import *
from system import plugin_system

# تعريف المتغيرات العامة
client = None
megabase = []  # ✅ تعريف متغير megabase هنا
# إضافة بعد تعريف client و megabase
import socket
import select

def is_internet_available():
    """التحقق من توفر اتصال بالإنترنت"""
    try:
        # محاولة الاتصال بـ Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

def wait_for_internet():
    """انتظار حتى يعود الاتصال بالإنترنت"""
    print("🌐 في انتظار عودة الاتصال بالإنترنت...")
    while not is_internet_available():
        print("⏳ لا يزال الاتصال مقطوعاً، جاري المحاولة مرة أخرى خلال 10 ثوان...")
        time.sleep(10)
    print("✅ عاد الاتصال بالإنترنت")

def safe_disconnect():
    """قطع الاتصال بأمان"""
    global client
    try:
        if client and hasattr(client, 'disconnect'):
            client.disconnect()
            print("✅ تم قطع الاتصال بأمان")
    except Exception as e:
        print(f"⚠️ خطأ أثناء قطع الاتصال: {e}")
    finally:
        client = None
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
    
def is_owner(jid):
    """التحقق إذا كان JID معيناً من مالكي البوت - الإصدار المصحح"""
    try:
        if not jid:
            print("❌ JID فارغ في is_owner")
            return False
            
        jid_str = str(jid).strip()
        print(f"🔍 is_owner التحقق من: '{jid_str}'")
        
        # استخراج Bare JID
        bare_jid = extract_bare_jid(jid_str)
        print(f"🔍 Bare JID للمقارنة: '{bare_jid}'")
        
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
        
def safe_decode(text, encoding='utf-8'):
    """فك ترميز النص بأمان مع دعم ترميزات متعددة"""
    if text is None:
        return ""
    
    if isinstance(text, str):
        return text
    
    if isinstance(text, bytes):
        try:
            return text.decode(encoding)
        except UnicodeDecodeError:
            try:
                # حاول الترميزات الشائعة
                for enc in ['utf-8', 'latin-1', 'windows-1256', 'cp1256', 'iso-8859-6']:
                    try:
                        return text.decode(enc)
                    except UnicodeDecodeError:
                        continue
                # إذا فشلت جميع المحاولات، استخدم تجاهل الأخطاء
                return text.decode('utf-8', errors='ignore')
            except Exception:
                return str(text, errors='ignore')
    
    return str(text)

def debug_handler(debug_type, text, severity=0):
    """معالج تصحيح محسّن للتعامل مع الترميز"""
    try:
        # تحويل severity إلى رقم إذا كانت نصاً
        try:
            if isinstance(severity, str):
                severity = int(severity)
        except (ValueError, TypeError):
            severity = 0
            
        # فك ترميز النص بأمان
        safe_text = safe_decode(text)
        
        # طباعة رسائل التصحيح المهمة فقط (باستخدام مقارنة رقمية صحيحة)
        if isinstance(severity, (int, float)) and severity <= 10:
            print(f"🔍 [{debug_type}] {safe_text[:200]}...")
    except Exception as e:
        print(f"❌ خطأ في معالج التصحيح: {e}")

def get_real_jid_from_megabase(room, nick):
    """الحصول على JID الحقيقي للمستخدم من megabase - نسخة محسنة"""
    try:
        print(f"🔍 البحث في megabase عن: Room={room}, Nick={nick}")
        
        for entry in megabase:
            if entry[0] == room and entry[1] == nick:
                real_jid = entry[4]
                print(f"🔍 وجد JID حقيقي: {real_jid}")
                
                if real_jid:
                    # تنظيف JID وإزالة المورد إذا كان موجوداً
                    if '/' in real_jid:
                        real_jid = real_jid.split('/')[0]
                    return real_jid
                else:
                    print(f"⚠️ JID حقيقي فارغ لـ {nick} في {room}")
        
        print(f"❌ لم يتم العثور على JID حقيقي لـ {nick} في {room}")
        return None
    except Exception as e:
        print(f"❌ خطأ في get_real_jid_from_megabase: {e}")
        return None

def message_handler(conn, message):
    """معالجة الرسائل الواردة - نسخة مصححة"""
    try:
        from_jid = str(message.getFrom())
        body = message.getBody()
        msg_type = message.getType()
        
        # 🔥 تجاهل الرسائل المرسلة من البوت نفسه
        if from_jid.endswith(f"/{BOT_NICKNAME}") or from_jid == BOT_JID:
            print(f"🔍 تجاهل رسالة من البوت نفسه: {from_jid}")
            return
        
        # فك ترميز النص بأمان
        safe_body = safe_decode(body)
        
        print(f"📥 رسالة واردة من {from_jid}: {safe_body}")
        
        # تجاهل الرسائل الفارغة
        if not safe_body:
            return
        
        # استخراج معلومات المرسل بشكل صحيح
        sender_bare = extract_bare_jid(from_jid)
        room = None
        nick = ""
        real_jid = None
        
        if msg_type == 'groupchat' and '/' in from_jid:
            # رسالة جماعية
            room_parts = from_jid.split('/', 1)
            room = room_parts[0]
            nick = room_parts[1] if len(room_parts) > 1 else ""
            print(f"🔍 رسالة جماعية من '{nick}' في {room}")
            
            # تجاهل الرسائل من البوت نفسه في الغرف
            if nick == BOT_NICKNAME:
                print(f"🔍 تجاهل رسالة جماعية من البوت نفسه: {nick}")
                return
            
            # الحصول على JID الحقيقي للمستخدم
            real_jid = get_real_jid_from_megabase(room, nick)
            print(f"🔍 JID الحقيقي للمستخدم: {real_jid}")
        else:
            # رسالة خاصة - نعتبر أن JID المرسل هو الغرفة الافتراضية
            room = from_jid  # في الرسائل الخاصة، نستخدم JID المرسل كـ "room"
            nick = from_jid.split('/')[1] if '/' in from_jid else sender_bare
            
            # تجاهل الرسائل الخاصة من البوت نفسه
            if sender_bare == extract_bare_jid(BOT_JID):
                print(f"🔍 تجاهل رسالة خاصة من البوت نفسه: {sender_bare}")
                return
            
            print(f"🔍 رسالة خاصة من '{nick}' - معالجة كغرفة: {room}")
        
        # معالجة الأوامر
        if safe_body.startswith('!'):
            print(f"🔧 معالجة أمر: {safe_body} من '{nick}' في {from_jid}")
            process_command(msg_type, from_jid, nick, safe_body[1:], message, real_jid)
            
    except Exception as e:
        print(f"❌ خطأ في معالجة الرسالة: {e}")
        import traceback
        traceback.print_exc()

def connect_and_authenticate():
    """الاتصال والخادم والمصادقة - نسخة محسنة"""
    global client
    
    try:
        # إنشاء العميل مع إعدادات الترميز
        jid = xmpp.JID(BOT_JID)
        client = xmpp.Client(jid.getDomain(), debug=[])
        
        # إعداد معالجات الترميز
        client.DEBUG = debug_handler
        
        # الاتصال
        print(f"🔗 جاري الاتصال بـ {SERVER}:{PORT}...")
        connection_result = client.connect(server=(SERVER, PORT), use_srv=False)
        
        if not connection_result:
            print("❌ فشل في الاتصال بالخادم")
            return False
        
        print("✅ تم الاتصال بنجاح، جاري المصادقة...")
        
        # المصادقة
        auth_result = client.auth(jid.getNode(), BOT_PASSWORD, resource="bot")
        
        if not auth_result:
            print("❌ فشل في المصادقة")
            return False
        
        print("✅ تم المصادقة بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def process_command(msg_type, jid, nick, command_text, original_message=None, real_jid=None):
    """معالجة الأوامر الواردة - النسخة المصححة"""
    try:
        print(f"🔧 معالجة أمر: {command_text} من '{nick}' في {jid}")
        
        # تقسيم النص إلى أمر ووسائط
        parts = command_text.strip().split(' ', 1)
        command = parts[0].strip().lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # 🔥 استخراج اسم الغرفة بشكل صحيح لكل أنواع الرسائل
        room = ""
        if msg_type == 'groupchat' and '/' in jid:
            # رسالة جماعية
            room = jid.split('/')[0]
        else:
            # رسالة خاصة - نستخدم JID كـ room
            room = jid
        
        print(f"🔍 تحليل الأمر: أمر={command}, وسائط={args}, غرفة={room}, مستخدم={nick}, نوع={msg_type}")
        
        # 🔥 استخدام JID الحقيقي إذا كان متاحاً للتحقق من المالك
        # إذا كان real_jid غير متوفر، نستخدم JID المرسل مع استخراج Bare JID
        check_jid = None
        if real_jid:
            check_jid = real_jid
            print(f"🔍 استخدام JID الحقيقي: {check_jid}")
        elif room and nick:
            # البحث عن JID الحقيقي من megabase
            check_jid = get_user_jid(room, nick)
            print(f"🔍 JID الحقيقي من megabase: {check_jid}")
        
        # إذا لم نجد JID حقيقي، نستخدم JID المرسل (لكن نستخرج Bare JID أولاً)
        if not check_jid:
            check_jid = extract_bare_jid(jid)
            print(f"🔍 استخدام JID المرسل (بعد التنظيف): {check_jid}")
            
        print(f"🔍 JID المستخدم للتحقق: {check_jid}")
        
        # التحقق من مالك البوت أولاً باستخدام JID الصحيح
        if is_owner(check_jid):
            print(f"✅ تم التعرف على المالك: {check_jid}")
            if process_owner_commands(msg_type, jid, nick, command, args, original_message):
                return
        # معالجة الأوامر العادية من خلال نظام البلاجنات
        from system import plugin_system
        
        for cmd in plugin_system.commands:
            level, cmd_name, func, min_args, help_text = cmd
            
            # مطابقة الأمر
            if cmd_name == command:
                # 🔥 التحقق من مستوى الصلاحية باستخدام المعلومات الكاملة
                user_level = get_user_permission_level(jid, nick, room)
                print(f"🔍 مستوى المستخدم للأمر {command}: {user_level} (مطلوب: {level})")
                
                if user_level >= level:
                    # التحقق من عدد الوسائط
                    if min_args > 0 and not args.strip():
                        send_msg(msg_type, jid, nick, f"❌ هذا الأمر يحتاج إلى وسائط. الاستخدام: !{command} {help_text.split(' - ')[-1] if ' - ' in help_text else '[وسائط]'}")
                        return
                    
                    # تنفيذ الأمر
                    try:
                        print(f"✅ تنفيذ الأمر: !{command} بواسطة '{nick}' (المستوى: {user_level})")
                        func(msg_type, jid, nick, args)
                    except Exception as e:
                        error_msg = f"❌ خطأ في تنفيذ الأمر: {str(e)}"
                        print(error_msg)
                        send_msg(msg_type, jid, nick, error_msg)
                    return
                else:
                    send_msg(msg_type, jid, nick, f"❌ ليس لديك الصلاحية الكافية لاستخدام هذا الأمر (مطلوب: {level}, لديك: {user_level})")
                    return
        
        # إذا لم يتم العثور على الأمر
        send_msg(msg_type, jid, nick, f"❌ الأمر '!{command}' غير معروف. اكتب '!مساعدة' لرؤية الأوامر المتاحة")
        
    except Exception as e:
        error_msg = f"❌ خطأ في معالجة الأمر: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        send_msg(msg_type, jid, nick, "❌ حدث خطأ في معالجة الأمر")

def debug_user_permissions(jid, nick, room):
    """تصحيح مفصل لصلاحيات المستخدم"""
    print(f"🎯 تصحيح الصلاحيات المفصل:")
    print(f"   - JID: {jid}")
    print(f"   - Nick: {nick}") 
    print(f"   - Room: {room}")
    
    clean_jid_val = clean_jid(jid)
    print(f"   - JID نظيف: {clean_jid_val}")
    
    # التحقق من المالكية المباشرة
    direct_owner = is_owner(clean_jid_val)
    print(f"   - مالك مباشر: {direct_owner}")
    
    # التحقق من JID الحقيقي
    real_jid = get_user_jid(room, nick) if room and nick else None
    print(f"   - JID حقيقي: {real_jid}")
    
    real_owner = False
    if real_jid:
        real_bare = clean_jid(real_jid.split('/')[0]) if '/' in real_jid else clean_jid(real_jid)
        real_owner = is_owner(real_bare)
        print(f"   - مالك من JID حقيقي: {real_owner}")
    
    # البحث في megabase
    megabase_info = None
    for entry in megabase:
        if entry[0] == room and entry[1] == nick:
            megabase_info = entry
            break
    
    print(f"   - معلومات Megabase: {megabase_info}")
    
    # حساب المستوى النهائي
    final_level = get_user_permission_level(jid, nick, room)
    print(f"   - المستوى النهائي: {final_level}")
    
    return final_level

def فحص_معلومات(msg_type, jid, nick, text):
    """دالة فحص المعلومات - النسخة النهائية"""
    try:
        room = jid.split('/')[0] if '/' in jid else ""
        
        # إذا كان nick فارغاً، نحاول استخراجه من jid
        if not nick and '/' in jid:
            nick = jid.split('/')[1]
        
        print(f"🔍 فحص معلومات: غرفة={room}, مستخدم={nick}, jid={jid}")
        
        if not room or not nick:
            send_msg(msg_type, jid, nick, "❌ لا يمكن العثور على معلومات الغرفة أو المستخدم")
            return
        
        # تشغيل التصحيح المفصل
        user_level = debug_user_permissions(jid, nick, room)
        
        # البحث في megabase
        user_info = None
        for entry in megabase:
            if entry[0] == room and entry[1] == nick:
                user_info = entry
                break
        
        # التحقق النهائي من المالكية
        is_owner_user = (is_owner(jid) or 
                        (room and nick and is_owner(get_user_jid(room, nick))))
        
        if user_info:
            info_msg = f"""🔍 معلومات المستخدم {nick}:

• الغرفة: {user_info[0]}
• الاسم: {user_info[1]}
• الصلاحية: {user_info[2]}
• الدور: {user_info[3]}
• JID الحقيقي: {user_info[4] or 'غير معروف'}
• مستوى التصريح: {user_level}
• مالك البوت: {'✅ نعم' if is_owner_user else '❌ لا'}
• نوع المالكية: {'مباشر' if is_owner(jid) else 'من خلال JID حقيقي' if is_owner_user else 'ليس مالك'}"""
        else:
            info_msg = f"❌ لم يتم العثور على معلومات للمستخدم '{nick}' في megabase"
            info_msg += f"\n🔍 حجم megabase: {len(megabase)} مستخدم"
            info_msg += f"\n🔍 مالك البوت: {'✅ نعم' if is_owner_user else '❌ لا'}"
            info_msg += f"\n🔍 مستوى التصريح: {user_level}"
        
        send_msg(msg_type, jid, nick, info_msg)
        
    except Exception as e:
        error_msg = f"❌ خطأ في فحص المعلومات: {str(e)}"
        print(error_msg)
        send_msg(msg_type, jid, nick, error_msg)
        
def debug_owner_instant(msg_type, jid, nick):
    """تصحيح فوري للتعرف على المالك"""
    room = jid.split('/')[0] if '/' in jid else ""
    
    result = []
    result.append("🔍 تصحيح فوري للتعرف على المالك:")
    
    # المعلومات الأساسية
    result.append(f"• JID: {jid}")
    result.append(f"• Nick: {nick}")
    result.append(f"• Room: {room}")
    
    # تنظيف JID
    clean_jid_val = clean_jid(jid)
    result.append(f"• JID النظيف: {clean_jid_val}")
    
    # التحقق المباشر
    direct_owner = is_owner(jid)
    result.append(f"• is_owner(jid): {direct_owner}")
    
    # البحث عن JID الحقيقي
    real_jid = get_user_jid(room, nick) if room and nick else None
    result.append(f"• JID الحقيقي: {real_jid}")
    
    if real_jid:
        real_bare = clean_jid(real_jid.split('/')[0]) if '/' in real_jid else clean_jid(real_jid)
        result.append(f"• JID الحقيقي النظيف: {real_bare}")
        real_owner = is_owner(real_bare)
        result.append(f"• is_owner(real_jid): {real_owner}")
    
    # المستوى النهائي
    user_level = get_user_permission_level(jid, nick, room)
    result.append(f"• مستوى التصريح النهائي: {user_level}")
    
    # BOT_OWNERS الحالي
    result.append(f"• BOT_OWNERS: {BOT_OWNERS}")
    
    send_msg(msg_type, jid, nick, "\n".join(result))
        
def list_rooms_command(msg_type, jid, nick):
    """عرض قائمة الغرف"""
    try:
        rooms = db_fetchall('SELECT room, auto_join, joined_at FROM rooms ORDER BY joined_at')
        
        if not rooms:
            send_msg(msg_type, jid, nick, "📋 لا توجد غرف مسجلة في قاعدة البيانات")
            return
        
        room_list = "📋 قائمة الغرف المسجلة:\n\n"
        for i, room in enumerate(rooms, 1):
            status = "✅ منضم" if room['auto_join'] else "❌ غير منضم"
            room_list += f"{i}. {room['room']} - {status}\n"
        
        send_msg(msg_type, jid, nick, room_list)
        
    except Exception as e:
        error_msg = f"❌ خطأ في عرض قائمة الغرف: {str(e)}"
        print(error_msg)
        send_msg(msg_type, jid, nick, error_msg)
        
def process_owner_commands(msg_type, jid, nick, command, args, original_message=None):
    """معالجة الأوامر الخاصة بالمالكين - نسخة محدثة"""
    try:
        owner_commands = {
            # أوامر الإدارة الأساسية
            'ايقاف': lambda: shutdown_bot(msg_type, jid, nick),
            'اعادة': lambda: restart_bot(msg_type, jid, nick),
            'فحص': lambda: فحص_معلومات(msg_type, jid, nick, args),
            
            # أوامر الغرف
            'قائمة_الغرف': lambda: list_rooms_command(msg_type, jid, nick),
            'اضافة_غرفة': lambda: add_room_command(msg_type, jid, nick, args),
            'حذف_غرفة': lambda: remove_room_command(msg_type, jid, nick, args),
            
            # أوامر التحديث
            'تحديث_القوائم': lambda: force_refresh_megabase(msg_type, jid, nick),
            # أوامر التصحيح
            'مقارنة': lambda: debug_system(msg_type, jid, nick, args),
            'تصحيح': lambda: debug_owner_detailed(msg_type, jid, nick),
            'فحص_مالك': lambda: verify_owner_status(msg_type, jid, nick),
            'اتصال': lambda: check_and_report_connection(msg_type, jid, nick),
            
            # أوامر المالكين
            'اضافة_مالك': lambda: add_owner_command(msg_type, jid, nick, args),
            'حذف_مالك': lambda: remove_owner_command(msg_type, jid, nick, args),
            'قائمة_المالكين': lambda: list_owners_command(msg_type, jid, nick),
                        # 🔥 إضافة الأمر الجديد هنا
            'قاعدة': lambda: debug_megabase(msg_type, jid, nick, args),
        }
        
        if command in owner_commands:
            owner_commands[command]()
            return True
        return False
    except Exception as e:
        print(f"❌ خطأ في معالجة أمر المالك: {e}")
        return False

def verify_owner_status(msg_type, jid, nick):
    """التحقق من حالة المالك"""
    room = jid.split('/')[0] if '/' in jid else ""
    
    is_direct_owner = is_owner(jid)
    real_jid = get_user_jid(room, nick) if room and nick else None
    is_real_owner = is_owner(real_jid) if real_jid else False
    user_level = get_user_permission_level(jid, nick, room)
    
    status_msg = f"""
🔐 تحقق حالة المالك:

• المستخدم: {nick}
• الغرفة: {room or 'خاص'}
• مالك مباشر: {'✅ نعم' if is_direct_owner else '❌ لا'}
• JID حقيقي: {real_jid or 'غير معروف'}
• مالك من JID حقيقي: {'✅ نعم' if is_real_owner else '❌ لا'}
• مستوى التصريح: {user_level}
• الحالة: {'🎯 تم التعرف عليك كمطور للبوت' if is_direct_owner or is_real_owner else '❌ لم يتم التعرف عليك كمطور'}
"""
    
    send_msg(msg_type, jid, nick, status_msg.strip())

def get_user_permission_level(jid, nick="", room=""):
    """تحديد مستوى التصريح للمستخدم - الإصدار المصحح"""
    try:
        print(f"🎯 get_user_permission_level: JID={jid}, Nick={nick}, Room={room}")
        
        # استخراج Bare JID من JID المدخل
        sender_bare_jid = extract_bare_jid(jid)
        print(f"🔍 Bare JID المستخرج: {sender_bare_jid}")
        
        # 🔥 التصحيح: إذا كان JID هو غرفة، نبحث عن JID المستخدم الحقيقي
        if room and '@conference.' in sender_bare_jid:
            print(f"⚠️ JID المدخل هو غرفة، جاري البحث عن JID المستخدم الحقيقي...")
            
            if nick:
                # البحث عن JID الحقيقي للمستخدم من megabase
                real_jid = get_user_jid(room, nick)
                print(f"🔍 JID الحقيقي المستخرج من megabase: {real_jid}")
                
                if real_jid:
                    # استخراج Bare JID من JID الحقيقي
                    real_bare_jid = extract_bare_jid(real_jid)
                    print(f"🔍 Bare JID الحقيقي: {real_bare_jid}")
                    
                    # التحقق من المالكية باستخدام JID الحقيقي
                    if is_owner(real_bare_jid):
                        print(f"✅ مستوى 10: مالك من خلال JID الحقيقي")
                        return OWNER_PERMISSION_LEVEL
                else:
                    print(f"⚠️ لم يتم العثور على JID حقيقي لـ {nick} في {room}")
        
        # التحقق الأول: المالكية المباشرة من JID المدخل (إذا لم يكن غرفة)
        if not '@conference.' in sender_bare_jid and is_owner(sender_bare_jid):
            print(f"✅ مستوى 10: مالك مباشر من JID")
            return OWNER_PERMISSION_LEVEL
        
        # 🔥 معالجة خاصة للرسائل الخاصة
        if not room and '/' not in jid:
            # إذا كانت رسالة خاصة وليست من غرفة
            print(f"🔍 رسالة خاصة - التحقق من المالكية المباشرة")
            if is_owner(sender_bare_jid):
                print(f"✅ مستوى 10: مالك من رسالة خاصة")
                return OWNER_PERMISSION_LEVEL
            else:
                print(f"🔍 مستوى 1: رسالة خاصة من غير مالك")
                return DEFAULT_PERMISSION_LEVEL
        
        # التحقق الثاني: إذا كانت رسالة جماعية أو تحتوي على معلومات غرفة
        if room and nick:
            print(f"🔍 التحقق من: Room={room}, Nick={nick}")
            
            # البحث عن JID الحقيقي للمستخدم من megabase
            real_jid = get_user_jid(room, nick)
            print(f"🔍 JID الحقيقي المستخرج من megabase: {real_jid}")
            
            if real_jid:
                # استخراج Bare JID من JID الحقيقي
                real_bare_jid = extract_bare_jid(real_jid)
                print(f"🔍 Bare JID الحقيقي: {real_bare_jid}")
                
                # التحقق من المالكية باستخدام JID الحقيقي
                if is_owner(real_bare_jid):
                    print(f"✅ مستوى 10: مالك من خلال JID الحقيقي")
                    return OWNER_PERMISSION_LEVEL
            else:
                print(f"⚠️ لم يتم العثور على JID حقيقي لـ {nick} في {room}")
            
            # إذا لم يكن مالك البوت، نتحقق من صلاحياته في الغرفة
            print(f"🔍 البحث في megabase عن: Room={room}, Nick={nick}")
            for entry in megabase:
                if entry[0] == room and entry[1] == nick:
                    affiliation = entry[2]
                    print(f"🔍 وجد في megabase: Affiliation={affiliation}")
                    
                    if affiliation == 'owner':
                        print(f"✅ مستوى 8: مالك الغرفة")
                        return ROOM_OWNER_LEVEL
                    elif affiliation == 'admin':
                        print(f"✅ مستوى 7: مشرف الغرفة")
                        return ADMIN_LEVEL
                    elif affiliation == 'moderator':
                        print(f"✅ مستوى 6: مدير في الغرفة")
                        return MODERATOR_LEVEL
                    elif affiliation == 'member':
                        print(f"✅ مستوى 5: عضو في الغرفة")
                        return MEMBER_LEVEL
                    else:
                        print(f"✅ مستوى 1: بدون صلاحية في الغرفة")
                        return DEFAULT_PERMISSION_LEVEL
        
        print(f"🔍 مستوى 1: افتراضي")
        return DEFAULT_PERMISSION_LEVEL
        
    except Exception as e:
        print(f"❌ خطأ في get_user_permission_level: {e}")
        import traceback
        traceback.print_exc()
        return DEFAULT_PERMISSION_LEVEL
        
def extract_user_info(room, nick, presence):
    """استخراج معلومات المستخدم من بيانات الحضور"""
    affiliation = 'none'
    role = 'none'
    jid = ''
    
    try:
        print(f"🔍 استخراج معلومات للمستخدم: '{nick}' في {room}")
        
        # استخراج معلومات MUC من الحضور
        x_tag = presence.getTag('x', namespace='http://jabber.org/protocol/muc#user')
        if x_tag:
            item_tag = x_tag.getTag('item')
            if item_tag:
                affiliation = safe_decode(item_tag.getAttr('affiliation') or 'none')
                role = safe_decode(item_tag.getAttr('role') or 'none')
                jid = safe_decode(item_tag.getAttr('jid') or '')
                print(f"✅ تم استخراج معلومات المستخدم: {nick} -> JID: {jid}, Affiliation: {affiliation}, Role: {role}")
            else:
                print(f"⚠️ لا يوجد item tag في presence لـ '{nick}'")
        else:
            print(f"⚠️ لا يوجد x tag في presence لـ '{nick}'")
            
    except Exception as e:
        print(f"❌ خطأ في استخراج معلومات المستخدم '{nick}': {e}")
    
    return [room, nick, affiliation, role, jid]

def auto_update_megabase(room, nick, presence):
    """تحديث تلقائي لـ megabase عند استقبال حضور - نسخة محسنة"""
    try:
        if not room or not nick:
            return
        
        # 🔥 تجاهل تحديثات البوت نفسه والمستخدمين غير المرغوب فيهم
        if nick == BOT_NICKNAME:
            print(f"🔍 تجاهل تحديث حضور البوت نفسه: {nick}")
            return
        
        # تجاهل nicks فارغة أو غير صالحة
        if not nick.strip() or len(nick.strip()) < 2:
            print(f"🔍 تجاهل nick غير صالح: '{nick}'")
            return
            
        user_info = extract_user_info(room, nick, presence)
        
        # إذا لم نتمكن من استخراج المعلومات، استخدم القيم الافتراضية
        if not user_info[4]:  # إذا كان JID فارغاً
            user_info = [room, nick, 'none', 'none', '']
            print(f"⚠️ لم يتم استخراج JID لـ {nick}، استخدام القيم الافتراضية")
        
        # تحديث أو إضافة المستخدم
        user_found = False
        for i, entry in enumerate(megabase):
            if entry[0] == room and entry[1] == nick:
                megabase[i] = user_info
                user_found = True
                print(f"✅ تم تحديث معلومات المستخدم في megabase: {nick} في {room} -> JID: {user_info[4]}")
                break
        
        if not user_found:
            megabase.append(user_info)
            print(f"✅ تم إضافة مستخدم جديد إلى megabase: {nick} في {room} -> JID: {user_info[4]}")
        
        # طباعة محتويات megabase للتdebug
        debug_megabase(room)
        
    except Exception as e:
        print(f"❌ خطأ في التحديث التلقائي لـ megabase: {e}")

def clean_bot_from_megabase():
    """تنظيف megabase من أي إدخالات للبوت"""
    global megabase
    initial_count = len(megabase)
    
    # إزالة أي إدخالات للبوت
    megabase = [entry for entry in megabase if entry[1] != BOT_NICKNAME]
    
    removed_count = initial_count - len(megabase)
    if removed_count > 0:
        print(f"🧹 تم تنظيف {removed_count} إدخال للبوت من megabase")
    
    return removed_count
    
def get_affiliation(jid, nick):
    """الحصول على صلاحية المستخدم في الغرفة"""
    for entry in megabase:
        if entry[0] == jid and entry[1] == nick:
            return entry[2]
    return 'none'

def get_role(jid, nick):
    """الحصول على دور المستخدم في الغرفة"""
    try:
        for entry in megabase:
            if entry[0] == jid and entry[1] == nick:
                return entry[3]
        return 'none'
    except Exception as e:
        print(f"❌ خطأ في get_role: {e}")
        return 'none'

def get_user_jid(room, nick):
    """الحصول على JID الحقيقي للمستخدم"""
    try:
        for entry in megabase:
            if entry[0] == room and entry[1] == nick:
                return entry[4]
        return None
    except Exception as e:
        print(f"❌ خطأ في get_user_jid: {e}")
        return None

def debug_megabase(msg_type, jid, nick, text):
    """عرض محتويات megabase للتصحيح"""
    if not is_owner(jid):
        send_msg(msg_type, jid, nick, "❌ هذا الأمر متاح للمالكين فقط")
        return
    
    room = jid.split('/')[0] if '/' in jid else ""
    
    debug_info = f"🔧 تصحيح megabase للغرفة {room}:\n\n"
    
    room_entries = [entry for entry in megabase if entry[0] == room]
    
    if room_entries:
        for i, entry in enumerate(room_entries, 1):
            debug_info += f"{i}. الاسم: {entry[1]}\n"
            debug_info += f"   الصلاحية: {entry[2]}\n"
            debug_info += f"   الدور: {entry[3]}\n"
            debug_info += f"   JID: {entry[4] or 'غير معروف'}\n"
            debug_info += f"   المستوى: {get_user_permission_level(room, entry[1], room)}\n\n"
    else:
        debug_info += "❌ لا توجد مدخلات للغرفة الحالية\n\n"
    
    debug_info += f"إجمالي المدخلات في megabase: {len(megabase)}"
    
    send_msg(msg_type, jid, nick, debug_info)

def send_msg(type, jid, nick, text):
    """إرسال رسالة إلى غرفة أو مستخدم - نسخة محسنة"""
    try:
        if not client:
            print("❌ لا يمكن إرسال الرسالة: العميل غير متصل")
            return
        
        # فك ترميز النص بأمان
        safe_text = safe_decode(text)
            
        if type == 'groupchat':
            # إرسال رسالة جماعية - نستخدم room JID فقط (بدون الnick)
            if '/' in jid:
                room_jid = jid.split('/')[0]
            else:
                room_jid = jid
                
            message = xmpp.Message(room_jid, safe_text, typ='groupchat')
            print(f"📤 إرسال رسالة جماعية إلى {room_jid}: {safe_text[:100]}...")
            
        else:
            # إرسال رسالة خاصة
            message = xmpp.Message(jid, safe_text, typ='chat')
            print(f"📤 إرسال رسالة خاصة إلى {jid}: {safe_text[:100]}...")
        
        client.send(message)
        print(f"✅ تم إرسال الرسالة بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ في إرسال الرسالة إلى {jid}: {e}")
        import traceback
        traceback.print_exc()

def send_smart_msg(msg_type, jid, nick, text):
    """إرسال رسالة ذكية (مرادف لـ send_msg للتوافق)"""
    send_msg(msg_type, jid, nick, text)
        
def send_smart_reply(msg_type, jid, nick, text, original_message=None):
    """إرسال رد ذكي مع الاحتفاظ بالسياق"""
    try:
        if msg_type == 'groupchat' and original_message and hasattr(original_message, 'getID'):
            # محاولة استخدام الرد المناسب إذا كان مدعوماً
            reply = xmpp.Message(jid, safe_decode(text), typ='groupchat')
            # يمكن إضافة المزيد من التحسينات للردود هنا
            client.send(reply)
        else:
            send_msg(msg_type, jid, nick, text)
    except Exception as e:
        print(f"❌ خطأ في الرد الذكي: {e}")
        send_msg(msg_type, jid, nick, text)

def debug_owner_detailed(msg_type, jid, nick):
    """تصحيح مفصل للتعرف على المالك"""
    room = jid.split('/')[0] if '/' in jid else ""
    
    debug_info = []
    debug_info.append("🔍 تصحيح مفصل للتعرف على المالك:")
    debug_info.append(f"• JID المدخل: {jid}")
    debug_info.append(f"• النيك: {nick}")
    debug_info.append(f"• الغرفة: {room}")
    
    # تنظيف JID
    clean_jid_val = clean_jid(jid)
    debug_info.append(f"• JID النظيف: {clean_jid_val}")
    
    # التحقق المباشر
    direct_check = is_owner(jid)
    debug_info.append(f"• التحقق المباشر: {direct_check}")
    
    # البحث عن JID الحقيقي
    real_jid = None
    if room and nick:
        real_jid = get_user_jid(room, nick)
        debug_info.append(f"• JID الحقيقي: {real_jid}")
        
        if real_jid:
            real_clean = clean_jid(real_jid.split('/')[0]) if '/' in real_jid else clean_jid(real_jid)
            debug_info.append(f"• JID الحقيقي النظيف: {real_clean}")
            
            real_check = is_owner(real_clean)
            debug_info.append(f"• التحقق من JID الحقيقي: {real_check}")
    
    # المستوى النهائي
    final_level = get_user_permission_level(jid, nick, room)
    debug_info.append(f"• المستوى النهائي: {final_level}")
    
    # معلومات megabase
    megabase_entry = None
    for entry in megabase:
        if entry[0] == room and entry[1] == nick:
            megabase_entry = entry
            break
    debug_info.append(f"• مدخل Megabase: {megabase_entry}")
    
    debug_info.append(f"• BOT_OWNERS: {BOT_OWNERS}")
    
    send_msg(msg_type, jid, nick, "\n".join(debug_info))

def force_refresh_megabase(msg_type, jid, nick):
    """فرض تحديث قائمة megabase"""
    try:
        room = jid.split('/')[0] if '/' in jid else ""
        
        if not room:
            send_msg(msg_type, jid, nick, "❌ هذا الأمر يعمل فقط في الغرف")
            return
        
        send_msg(msg_type, jid, nick, "🔄 جاري تحديث قائمة المستخدمين في الغرفة...")
        
        # إرسال طلب معلومات الغرفة
        iq = xmpp.Iq('get', to=room)
        iq.addChild('query', namespace='http://jabber.org/protocol/muc#admin')
        iq.setID(f"refresh-{int(time.time())}")
        
        def refresh_callback(conn, iq_stanza):
            try:
                if iq_stanza.getType() == 'result':
                    users_found = 0
                    query = iq_stanza.getQuery()
                    if query:
                        items = query.getChildren()
                        for item in items:
                            if item.getName() == 'item':
                                user_nick = item.getAttr('nick') or ''
                                user_affiliation = item.getAttr('affiliation') or 'none'
                                user_role = item.getAttr('role') or 'none'
                                user_jid = item.getAttr('jid') or ''
                                
                                if user_nick and user_nick != BOT_NICKNAME:
                                    # تحديث أو إضافة المستخدم في megabase
                                    user_found = False
                                    for i, entry in enumerate(megabase):
                                        if entry[0] == room and entry[1] == user_nick:
                                            megabase[i] = [room, user_nick, user_affiliation, user_role, user_jid]
                                            user_found = True
                                            break
                                    
                                    if not user_found:
                                        megabase.append([room, user_nick, user_affiliation, user_role, user_jid])
                                    
                                    users_found += 1
                    
                    send_msg(msg_type, jid, nick, f"✅ تم تحديث قائمة المستخدمين: {users_found} مستخدم")
                    print(f"✅ تم تحديث megabase: {users_found} مستخدم في {room}")
                    debug_megabase(room)
                else:
                    send_msg(msg_type, jid, nick, "❌ فشل في تحديث قائمة المستخدمين")
            except Exception as e:
                print(f"❌ خطأ في تحديث القوائم: {e}")
                send_msg(msg_type, jid, nick, f"❌ خطأ في التحديث: {str(e)}")
        
        client.RegisterHandler('iq', refresh_callback, iq.getID())
        client.send(iq)
        
    except Exception as e:
        send_msg(msg_type, jid, nick, f"❌ خطأ في التحديث: {str(e)}")

def debug_system(msg_type, jid, nick, args):
    """تصحيح النظام وعرض معلومات التdebug"""
    try:
        room = jid.split('/')[0] if '/' in jid else ""
        
        # إذا كان nick فارغاً، نحاول استخراجه من jid
        if not nick and '/' in jid:
            nick = jid.split('/')[1]
        
        # الحصول على JID الحقيقي
        real_jid = get_real_jid_from_megabase(room, nick) if room and nick else None
        
        # عرض معلومات المستخدم الحالي
        user_info = f"""
🔍 معلومات التصحيح:

• المستخدم: {nick}
• الغرفة: {room}
• JID: {jid}
• JID الحقيقي: {real_jid or 'غير معروف'}
• مستوى التصريح: {get_user_permission_level(jid, nick, room)}
• مالك البوت: {'✅ نعم' if is_owner(real_jid if real_jid else clean_jid(jid)) else '❌ لا'}
• حجم megabase: {len(megabase)} مستخدم
"""
        
        # عرض مستخدمي الغرفة
        if room:
            room_users = [entry for entry in megabase if entry[0] == room]
            user_info += f"• مستخدمي الغرفة في megabase: {len(room_users)}\n"
            
            for user in room_users:
                user_info += f"  - {user[1]} (affiliation: {user[2]}, role: {user[3]}, JID: {user[4]})\n"
            
            if len(room_users) == 0:
                user_info += "  ⚠️ لا يوجد مستخدمين مسجلين في megabase\n"
        
        send_msg(msg_type, jid, nick, user_info.strip())
        
    except Exception as e:
        send_msg(msg_type, jid, nick, f"❌ خطأ في التصحيح: {str(e)}")

def check_and_report_connection(msg_type, jid, nick):
    """فحص وإبلاغ حالة الاتصال"""
    connection_status = check_connection_status()
    room_status = len([entry for entry in megabase if '@conference' in entry[0]])
    
    status_msg = f"""
📊 حالة الاتصال:
• اتصال الخادم: {'✅ متصل' if connection_status else '❌ غير متصل'}
• الغرف النشطة: {room_status}
• البوت: {'🟢 نشط' if connection_status else '🔴 غير نشط'}
"""
    
    send_msg(msg_type, jid, nick, status_msg.strip())
    
    # إذا كان متصلاً لكن ليس في غرف، نعيد الانضمام
    if connection_status and room_status == 0:
        send_msg(msg_type, jid, nick, "🔄 جاري إعادة الانضمام إلى الغرف...")
        join_rooms()

def shutdown_bot(msg_type, jid, nick):
    """إيقاف البوت"""
    send_msg(msg_type, jid, nick, "🛑 جاري إيقاف البوت...")
    print("🛑 إيقاف البوت بناء على طلب المالك...")
    if client:
        client.disconnect()
    sys.exit(0)

def send_bot_status(msg_type, jid, nick):
    """إرسال حالة البوت"""
    status_msg = f"""
🤖 حالة البوت:
• المالك: {nick}
• الغرف النشطة: {len([entry for entry in megabase if '@conference' in entry[0]])}
• الأوامر المدمجة: {len(plugin_system.commands)}
• الذاكرة: نشطة
• البوت: يعمل بشكل طبيعي
    """
    send_msg(msg_type, jid, nick, status_msg.strip())

def restart_bot(msg_type, jid, nick):
    """إعادة تشغيل البوت (نظري)"""
    send_msg(msg_type, jid, nick, "🔄 إعادة التشغيل تتطلب إعادة تشغيل البرنامج يدوياً")

def presence_handler(conn, presence):
    """معالجة تحديثات الحضور - نسخة محسنة"""
    try:
        from_jid = str(presence.getFrom())
        presence_type = presence.getType()
        
        print(f"📥 حضور وارد من {from_jid} - النوع: {presence_type}")
        
        # 🔥 تجاهل الحضور الخاص بالبوت نفسه تماماً
        if from_jid.endswith(f"/{BOT_NICKNAME}") or from_jid == BOT_JID:
            print(f"🔍 تجاهل حضور البوت نفسه: {from_jid}")
            return
        
        # تجاهل الحضور من الخادم أو عناوين غير مستخدمة
        if not from_jid or '@' not in from_jid:
            print(f"🔍 تجاهل حضور غير صالح: {from_jid}")
            return
        
        # تحديث قائمة مستخدمي الغرف (megabase)
        if '/' in from_jid:
            room, nick = from_jid.split('/', 1)
            
            # 🔥 تجاهل إذا كان البوت هو المرسل
            if nick == BOT_NICKNAME:
                print(f"🔍 تجاهل حضور البوت في الغرفة: {from_jid}")
                return
            
            if presence_type == 'unavailable':
                # إزالة المستخدم من القائمة
                print(f"🗑️ إزالة المستخدم '{nick}' من {room}")
                remove_user_from_megabase(room, nick)
            else:
                # تحديث أو إضافة المستخدم
                print(f"➕ تحديث/إضافة المستخدم '{nick}' في {room}")
                auto_update_megabase(room, nick, presence)
        
        # معالجة حضور البلاجنات
        for handler in plugin_system.presence_handlers:
            try:
                handler(conn, presence)
            except Exception as e:
                print(f"❌ خطأ في معالج الحضور: {e}")
                
    except Exception as e:
        print(f"❌ خطأ في معالجة الحضور: {e}")

def muc_presence_handler(conn, presence):
    """معالجة حضور الغرف بشكل منفصل - دالة محسنة"""
    try:
        from_jid = str(presence.getFrom())
        presence_type = presence.getType()
        
        # 🔥 تجاهل حضور البوت نفسه في الغرف
        if from_jid.endswith(f"/{BOT_NICKNAME}"):
            print(f"🔍 حضور البوت في الغرفة: {from_jid} - النوع: {presence_type}")
            
            if presence_type == 'error':
                error_msg = presence.getError()
                print(f"❌ خطأ في حضور البوت: {error_msg}")
                # إعادة المحاولة بعد فترة
                time.sleep(10)
                join_rooms()
            elif presence_type == 'unavailable':
                print(f"⚠️ البوت أصبح غير متاح في الغرفة: {from_jid}")
                # إعادة الانضمام بعد فترة
                time.sleep(5)
                room_jid = from_jid.split('/')[0]
                rejoin_room(room_jid)
            
            # 🔥 لا نقوم بتحديث megabase للبوت نفسه
            return
                
    except Exception as e:
        print(f"❌ خطأ في معالجة حضور الغرف: {e}")

def rejoin_room(room_jid):
    """إعادة الانضمام إلى غرفة محددة"""
    try:
        print(f"🔄 إعادة الانضمام إلى الغرفة: {room_jid}")
        
        # إرسال حضور الانضمام مع إعدادات MUC
        presence = xmpp.Presence(to=f"{room_jid}/{BOT_NICKNAME}")
        x_element = presence.addChild('x', namespace='http://jabber.org/protocol/muc')
        
        # إضافة تاريخ إذا كان مطلوباً لتجنب "الانضمام السريع"
        history_element = xmpp.Node('history', {'maxstanzas': '0'})
        x_element.addChild(node=history_element)
        
        client.send(presence)
        print(f"✅ تم إرسال طلب إعادة الانضمام إلى: {room_jid}")
        
    except Exception as e:
        print(f"❌ خطأ في إعادة الانضمام إلى {room_jid}: {e}")

def ensure_user_in_megabase(room, nick):
    """التأكد من وجود المستخدم في megabase، وإضافته إذا لم يكن موجوداً"""
    global megabase
    
    # التحقق إذا كان المستخدم موجوداً بالفعل
    for entry in megabase:
        if entry[0] == room and entry[1] == nick:
            return True
    
    # إذا لم يكن موجوداً، نطلب معلومات الحضور من الخادم
    print(f"🔍 المستخدم '{nick}' غير موجود في megabase، جاري طلب المعلومات...")
    
    try:
        # إرسال طلب معلومات الغرفة
        iq = xmpp.Iq('get', to=room)
        iq.addChild('query', namespace='http://jabber.org/protocol/muc#admin')
        iq.setID(f"admin-{int(time.time())}")
        
        def admin_callback(conn, iq_stanza):
            if iq_stanza.getType() == 'result':
                print(f"✅ تم استلام معلومات الغرفة لـ {room}")
                # هنا يمكن معالجة الرد للحصول على قائمة المستخدمين
            else:
                print(f"❌ فشل في الحصول على معلومات الغرفة")
        
        client.RegisterHandler('iq', admin_callback, iq.getID())
        client.send(iq)
        
    except Exception as e:
        print(f"❌ خطأ في طلب معلومات الغرفة: {e}")
    
    return False

def refresh_room_users(room):
    """تحديث قائمة مستخدمي الغرفة"""
    try:
        print(f"🔄 جاري تحديث مستخدمي الغرفة: {room}")
        
        # إرسال طلب للحصول على قائمة المستخدمين
        iq = xmpp.Iq('get', to=room)
        iq.addChild('query', namespace='http://jabber.org/protocol/muc#admin')
        iq.setID(f"refresh-{int(time.time())}")
        
        def refresh_callback(conn, iq_stanza):
            if iq_stanza.getType() == 'result':
                print(f"✅ تم تحديث قائمة مستخدمي {room}")
                # يمكن إضافة معالجة للرد هنا
            else:
                print(f"❌ فشل في تحديث قائمة المستخدمين")
        
        client.RegisterHandler('iq', refresh_callback, iq.getID())
        client.send(iq)
        
    except Exception as e:
        print(f"❌ خطأ في تحديث مستخدمي الغرفة: {e}")

def update_megabase(room, nick, presence):
    """تحديث قائمة مستخدمي الغرف"""
    global megabase
    
    # البحث عن المستخدم في القائمة
    for i, entry in enumerate(megabase):
        if entry[0] == room and entry[1] == nick:
            # تحديث البيانات
            megabase[i] = extract_user_info(room, nick, presence)
            return
    
    # إضافة مستخدم جديد
    user_info = extract_user_info(room, nick, presence)
    megabase.append(user_info)

def remove_user_from_megabase(room, nick):
    """إزالة مستخدم من قائمة الغرفة"""
    global megabase
    initial_count = len(megabase)
    megabase = [entry for entry in megabase if not (entry[0] == room and entry[1] == nick)]
    removed_count = initial_count - len(megabase)
    if removed_count > 0:
        print(f"✅ تم إزالة {removed_count} مستخدم من megabase")

def iq_handler(conn, iq):
    """معالجة طلبات IQ - نسخة محسنة"""
    try:
        iq_type = iq.getType()
        iq_id = iq.getID()
        iq_from = str(iq.getFrom())
        
        # تجاهل أخطاء الانضمام السريع (غير مهمة)
        if (iq_type == 'error' and 
            'muc' in str(iq.getQueryNS()) and 
            'الانضمام السريع ممنوع' in str(iq)):
            print(f"⚠️  تم رفض الانضمام السريع - هذا طبيعي")
            return True
        
        # معالجة IQ من قبل البلاجنات
        for handler in plugin_system.iq_handlers:
            try:
                result = handler(conn, iq)
                if result:
                    return result
            except Exception as e:
                print(f"❌ خطأ في معالج IQ: {e}")
                
    except Exception as e:
        print(f"❌ خطأ في معالجة IQ: {e}")
    
    return False

def check_and_update_presence():
    """التحقق وتحديث حالة الحضور بشكل دوري - دالة جديدة"""
    if client and client.isConnected():
        # إرسال حضور لتحديث الحالة
        presence = xmpp.Presence(show='chat', status=BOT_STATUS)
        client.send(presence)
        print("🔄 تم تحديث حالة الحضور")
        return True
    return False

def reconnect_if_needed():
    """إعادة الاتصال إذا كان البوت غير متصل - نسخة محسنة"""
    global client
    
    # التحقق أولاً من اتصال الإنترنت
    if not is_internet_available():
        print("🌐 الاتصال بالإنترنت مقطوع...")
        wait_for_internet()
    
    # التحقق من اتصال XMPP
    connection_ok = False
    try:
        if client and hasattr(client, 'isConnected'):
            connection_ok = client.isConnected()
            # اختبار إضافي بإرسال حضور
            if connection_ok:
                test_presence = xmpp.Presence(show='chat', status="اختبار اتصال")
                client.send(test_presence)
                print("✅ اتصال XMPP نشط")
    except Exception as e:
        print(f"❌ اتصال XMPP معطل: {e}")
        connection_ok = False
    
    if not connection_ok:
        print("🔌 فقدان اتصال XMPP - جاري إعادة الاتصال...")
        safe_disconnect()
        
        # انتظار قبل إعادة المحاولة
        time.sleep(5)
        
        # المحاولة عدة مرات
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"🔄 محاولة إعادة الاتصال {attempt + 1}/{max_attempts}...")
            try:
                if connect_and_authenticate():
                    set_initial_presence()
                    join_rooms()
                    print("✅ تمت إعادة الاتصال بنجاح!")
                    return True
                else:
                    print(f"❌ فشلت محاولة {attempt + 1}")
                    time.sleep(10)  # انتظار 10 ثواني قبل المحاولة التالية
            except Exception as e:
                print(f"❌ خطأ في محاولة {attempt + 1}: {e}")
                time.sleep(10)
        
        print("❌ فشلت جميع محاولات إعادة الاتصال")
        return False
    
    return True
    
def timer_loop():
    """حلقة المؤقتات لتشغيل الدوال الدورية - نسخة محسنة"""
    presence_counter = 0
    connection_check_counter = 0
    
    while True:
        try:
            # تحديث الحضور كل 5 دقائق
            presence_counter += 1
            if presence_counter >= 5:  # كل 5 دقائق
                check_and_update_presence()
                presence_counter = 0
            
            # التحقق من الاتصال كل دقيقة
            connection_check_counter += 1
            if connection_check_counter >= 1:  # كل دقيقة
                reconnect_if_needed()
                connection_check_counter = 0
            
            # تشغيل دوال المؤقتات من البلاجنات
            for timer_func in plugin_system.timer_functions:
                try:
                    timer_func()
                except Exception as e:
                    print(f"❌ خطأ في دالة المؤقت: {e}")
            
            time.sleep(60)  # تشغيل كل دقيقة
            
        except Exception as e:
            print(f"❌ خطأ في حلقة المؤقتات: {e}")
            time.sleep(60)

def setup_handlers():
    """إعداد معالجات الأحداث - نسخة محسنة"""
    # إعداد معالجات الرسائل
    client.RegisterHandler('message', message_handler)
    
    # إعداد معالجات الحضور
    client.RegisterHandler('presence', presence_handler)
    client.RegisterHandler('presence', muc_presence_handler)  # أضف هذا السطر
    
    # إعداد معالجات IQ
    client.RegisterHandler('iq', iq_handler)
    
    print("✅ تم إعداد معالجات الأحداث")

def join_rooms():
    """الانضمام إلى الغرف المحددة - نسخة محسنة"""
    # الحصول على الغرف من قاعدة البيانات
    rooms = db_fetchall('SELECT room FROM rooms WHERE auto_join = 1')
    
    if not rooms:
        print("❌ لا توجد غرف مضمّنة في قاعدة البيانات للانضمام التلقائي")
        return
    
    print(f"🔍 العثور على {len(rooms)} غرفة للانضمام...")
    
    for room in rooms:
        room_jid = room['room']
        
        # التحقق من أن الغرفة هي غرفة مؤتمر صحيحة
        if not is_valid_conference_room(room_jid):
            print(f"⚠️  تجاهل غرفة غير صالحة: {room_jid}")
            continue
            
        try:
            print(f"🚪 جاري الانضمام إلى الغرفة: {room_jid}")
            
            # إرسال حضور الانضمام مع إعدادات MUC محسنة
            presence = xmpp.Presence(to=f"{room_jid}/{BOT_NICKNAME}")
            x_element = presence.addChild('x', namespace='http://jabber.org/protocol/muc')
            
            # إضافة معلومات إضافية لتفادي مشاكل الانضمام
            history_element = xmpp.Node('history', {'maxstanzas': '0'})
            x_element.addChild(node=history_element)
            
            client.send(presence)
            print(f"✅ تم إرسال حضور الانضمام إلى: {room_jid}")
            
            # انتظار أطول بين الطلبات لتجنب الانضمام السريع
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ خطأ في الانضمام إلى {room_jid}: {e}")
def join_room_command(msg_type, jid, nick, args):
    """الانضمام إلى غرفة محددة"""
    try:
        if not args.strip():
            send_msg(msg_type, jid, nick, "❌ يرجى تحديد اسم الغرفة. الاستخدام: !انضمام room@conference.server")
            return
        
        room_jid = args.strip()
        
        # التحقق من أن الغرفة هي غرفة مؤتمر صحيحة
        if not is_valid_conference_room(room_jid):
            send_msg(msg_type, jid, nick, f"❌ JID الغرفة غير صالح: {room_jid}")
            return
        
        # التحقق من اتصال البوت أولاً
        if not check_connection_status():
            send_msg(msg_type, jid, nick, "❌ البوت غير متصل بالخادم حالياً")
            return
        
        send_msg(msg_type, jid, nick, f"🔄 جاري الانضمام إلى الغرفة: {room_jid}")
        
        # إضافة الغرفة إلى قاعدة البيانات أولاً
        result = db_execute(
            'INSERT OR REPLACE INTO rooms (room, auto_join) VALUES (?, 1)',
            (room_jid,)
        )
        
        if not result:
            send_msg(msg_type, jid, nick, f"❌ فشل في إضافة الغرفة إلى قاعدة البيانات: {room_jid}")
            return
        
        # الانضمام إلى الغرفة
        try:
            print(f"🚪 جاري الانضمام إلى الغرفة: {room_jid}")
            
            # إرسال حضور الانضمام مع إعدادات MUC
            presence = xmpp.Presence(to=f"{room_jid}/{BOT_NICKNAME}")
            x_element = presence.addChild('x', namespace='http://jabber.org/protocol/muc')
            
            # إضافة تاريخ لتجنب مشاكل الانضمام السريع
            history_element = xmpp.Node('history', {'maxstanzas': '0'})
            x_element.addChild(node=history_element)
            
            client.send(presence)
            print(f"✅ تم إرسال حضور الانضمام إلى: {room_jid}")
            
            send_msg(msg_type, jid, nick, f"✅ تم إرسال طلب الانضمام إلى: {room_jid}")
            
            # انتظار قليل ثم التحقق من الانضمام
            time.sleep(3)
            
        except Exception as e:
            error_msg = f"❌ خطأ في الانضمام إلى {room_jid}: {str(e)}"
            print(error_msg)
            send_msg(msg_type, jid, nick, error_msg)
            
    except Exception as e:
        error_msg = f"❌ خطأ في أمر الانضمام: {str(e)}"
        print(error_msg)
        send_msg(msg_type, jid, nick, error_msg)
        
def is_valid_conference_room(room_jid):
    """التحقق من أن JID الغرفة صالح للانضمام"""
    if not room_jid:
        return False
    
    # يجب أن تكون غرفة المؤتمر تحت نطاق conference أو muc
    room_jid_lower = room_jid.lower()
    return ('@conference.' in room_jid_lower or 
            '@muc.' in room_jid_lower or
            '@room.' in room_jid_lower)

def setup_initial_rooms():
    """إعداد الغرف الأولية بشكل صحيح"""
    try:
        # تنظيف الغرف غير الصالحة من قاعدة البيانات
        rooms = db_fetchall('SELECT room FROM rooms WHERE auto_join = 1')
        for room in rooms:
            room_jid = room['room']
            if not is_valid_conference_room(room_jid):
                print(f"🗑️ إزالة غرفة غير صالحة: {room_jid}")
                db_execute('DELETE FROM rooms WHERE room = ?', (room_jid,))
        
        # إضافة غرف افتراضية إذا لم توجد
        default_rooms = [
            'egypt-syria@conference.jabber.ru',
            # أضف غرف أخرى صالحة هنا
        ]
        
        for room_jid in default_rooms:
            existing = db_fetchone('SELECT room FROM rooms WHERE room = ?', (room_jid,))
            if not existing:
                db_execute('INSERT INTO rooms (room, auto_join) VALUES (?, 1)', (room_jid,))
                print(f"✅ تم إضافة غرفة افتراضية: {room_jid}")
                
    except Exception as e:
        print(f"❌ خطأ في إعداد الغرف: {e}")
        
def set_initial_presence():
    """تعيين الحضور الأولي - نسخة محسنة"""
    presence = xmpp.Presence(show='chat', status=BOT_STATUS)
    client.send(presence)
    print("✅ تم تعيين الحضور الأولي - متصل ونشط")

# إضافة دوال توافقية للبلاجنات القديمة
def get_level(jid, nick):
    """دالة توافقية للبلاجنات القديمة - استخدام get_user_permission_level بدلاً منها"""
    return get_user_permission_level(jid, nick, jid.split('/')[0] if '/' in jid else "")

def check_connection_status():
    """التحقق من حالة اتصال البوت"""
    global client
    try:
        if client and hasattr(client, 'isConnected'):
            connected = client.isConnected()
            print(f"🔍 حالة الاتصال: {'✅ متصل' if connected else '❌ غير متصل'}")
            return connected
        print("🔍 حالة الاتصال: ❌ العميل غير موجود")
        return False
    except Exception as e:
        print(f"🔍 خطأ في التحقق من الاتصال: {e}")
        return False

def send_connection_test():
    """إرسال اختبار اتصال"""
    try:
        # إرسال حضور عام للتحقق من الاتصال
        presence = xmpp.Presence(show='chat', status="البوت يعمل بشكل طبيعي")
        client.send(presence)
        print("✅ تم إرسال اختبار الاتصال")
        return True
    except Exception as e:
        print(f"❌ فشل اختبار الاتصال: {e}")
        return False
def enhanced_connect_and_authenticate():
    """اتصال ومصادقة محسنة مع التعامل مع الأخطاء"""
    global client
    
    try:
        # التحقق من الإنترنت أولاً
        if not is_internet_available():
            print("🌐 انتظار اتصال الإنترنت...")
            wait_for_internet()
        
        # إنشاء العميل مع إعدادات الترميز
        jid = xmpp.JID(BOT_JID)
        client = xmpp.Client(jid.getDomain(), debug=[])
        
        # إعداد معالجات الترميز
        client.DEBUG = debug_handler
        
        # إعداد مهلة الاتصال
        client.setTimeout(10)
        
        # الاتصال
        print(f"🔗 جاري الاتصال بـ {SERVER}:{PORT}...")
        connection_result = client.connect(server=(SERVER, PORT), use_srv=False)
        
        if not connection_result:
            print("❌ فشل في الاتصال بالخادم")
            return False
        
        print("✅ تم الاتصال بنجاح، جاري المصادقة...")
        
        # المصادقة
        auth_result = client.auth(jid.getNode(), BOT_PASSWORD, resource="bot")
        
        if not auth_result:
            print("❌ فشل في المصادقة")
            return False
        
        print("✅ تم المصادقة بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False
        
def main():
    """الدالة الرئيسية - نسخة محسنة"""
    print("🚀 بدء تشغيل بوت XMPP العربي المحسن...")
    
    # تعيين المتغيرات العالمية للبلاجنات
    global_vars = {
        'megabase': megabase,
        'client': client,
        'send_msg': send_msg,
        'send_smart_msg': send_smart_msg,
        'send_smart_reply': send_smart_reply,
        'get_user_permission_level': get_user_permission_level,
        'get_affiliation': get_affiliation,
        'get_role': get_role,
        'get_user_jid': get_user_jid,
        'get_real_jid_from_megabase': get_real_jid_from_megabase,
        'is_owner': is_owner,
        'clean_jid': clean_jid,
        # إضافة دوال قاعدة البيانات
        'db_execute': db_execute,
        'db_fetchone': db_fetchone,
        'db_fetchall': db_fetchall,
        'BOT_NICKNAME': BOT_NICKNAME,
        # دوال التصريح الجديدة
        'get_user_permission': get_user_permission,
        'set_user_permission': set_user_permission,
        'remove_user_permission': remove_user_permission,
        # دوال توافقية للبلاجنات القديمة
        'get_level': get_level,
        # دوال اتصال جديدة
        'check_connection_status': check_connection_status,
        'reconnect_if_needed': reconnect_if_needed,  # إضافة هذه
        'is_internet_available': is_internet_available,  # وإضافة هذه
    }
    
        # 🔥 تنظيف megabase من أي إدخالات سابقة للبوت
    clean_bot_from_megabase()
    
    plugin_system.set_global_vars(global_vars)
    
    # تحميل البلاجنات
    plugin_system.load_plugins()
    
    # إعداد الغرف الأولية
    setup_initial_rooms()
    
    
    # الاتصال بالخادم
    if not connect_and_authenticate():
        print("❌ فشل في الاتصال بالخادم - إعادة المحاولة...")
        # المحاولة مرة أخرى مع إعادة الاتصال
        time.sleep(10)
        if not reconnect_if_needed():
            print("❌ فشل نهائي في الاتصال")
            return
    
    print("✅ تم الاتصال بنجاح - التحقق من إرسال الحضور...")
    
    # إرسال اختبار الاتصال
    if not send_connection_test():
        print("❌ فشل في إرسال الحضور الاختباري")
        # المحاولة مع إعادة الاتصال
        if not reconnect_if_needed():
            return
    
    # إعداد المعالجات
    setup_handlers()
    
    # تعيين الحضور الأولي
    set_initial_presence()
    
    # الانضمام إلى الغرف
    join_rooms()
    
    # بدء حلقة المؤقتات في خيط منفصل
    timer_thread = threading.Thread(target=timer_loop, daemon=True)
    timer_thread.start()
    
    print("✅ البوت المحسن يعمل وجاهز لاستقبال الأوامر")
    
    # إرسال حضور نهائي للتأكد
    time.sleep(3)
    send_connection_test()
    
    # البقاء في حلقة الاستقبال مع التحقق من الاتصال
    try:
        reconnect_counter = 0
        while True:
            try:
                client.Process(1)
                
                # التحقق من الاتصال كل 10 ثواني في الحلقة الرئيسية
                reconnect_counter += 1
                if reconnect_counter >= 10:  # كل 10 ثواني
                    if not check_connection_status():
                        print("⚠️ فقدان الاتصال في الحلقة الرئيسية - جاري الإصلاح...")
                        reconnect_if_needed()
                    reconnect_counter = 0
                    
            except Exception as e:
                print(f"❌ خطأ في معالجة الرسائل: {e}")
                if not reconnect_if_needed():
                    print("❌ فشل في إعادة الاتصال، جاري المحاولة مرة أخرى...")
                    time.sleep(10)
                
    except KeyboardInterrupt:
        print("⏹️ إيقاف البوت...")
        safe_disconnect()
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()
        safe_disconnect()

if __name__ == "__main__":
    main()
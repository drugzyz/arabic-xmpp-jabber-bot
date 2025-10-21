# [file name]: system.py
# -*- coding: utf-8 -*-

import os
import sys
import importlib
import inspect
from config import PLUGINS_DIR

class PluginSystem:
    def __init__(self):
        self.plugins = {}
        self.commands = []
        self.presence_handlers = []
        self.message_handlers = []
        self.iq_handlers = []
        self.timer_functions = []
        self.global_vars = {}
        
    def set_global_vars(self, global_vars):
        """تعيين المتغيرات العالمية للبلاجنات"""
        self.global_vars = global_vars
        
    def load_plugins(self):
        """تحميل جميع البلاجنات من المجلد المخصص"""
        print(f"🔧 جاري تحميل البلاجنات من {PLUGINS_DIR}...")
        
        if not os.path.exists(PLUGINS_DIR):
            print(f"❌ مجلد البلاجنات غير موجود: {PLUGINS_DIR}")
            return
        
        # إضافة مسار البلاجنات إلى Python path
        if PLUGINS_DIR not in sys.path:
            sys.path.insert(0, PLUGINS_DIR)
        
        # تحميل كل ملف .py كمبلجن
        for filename in os.listdir(PLUGINS_DIR):
            if filename.endswith('.py') and filename != '__init__.py':
                plugin_name = filename[:-3]  # إزالة .py
                self.load_plugin(plugin_name)
        
        print(f"✅ تم تحميل {len(self.plugins)} بلاجن")
        
    def load_plugin(self, plugin_name):
        """تحميل بلجن معين"""
        try:
            # استيراد البلجن
            module = importlib.import_module(plugin_name)
            
            # تهيئة البلجن إذا كانت الدالة موجودة
            if hasattr(module, 'init_plugin'):
                module.init_plugin(self.global_vars)
            
            # استدعاء دالة execute إذا كانت موجودة
            if hasattr(module, 'execute'):
                commands = module.execute()
                if commands:
                    self.commands.extend(commands)
                    print(f"✅ تم تحميل {len(commands)} أمر من {plugin_name}")
            
            # جمع معالجات الحضور
            if hasattr(module, 'presence_control'):
                self.presence_handlers.extend(module.presence_control)
                
            # جمع معالجات الرسائل
            if hasattr(module, 'message_act_control'):
                self.message_handlers.extend(module.message_act_control)
                
            # جمع معالجات IQ
            if hasattr(module, 'iq_control'):
                self.iq_handlers.extend(module.iq_control)
                
            # جمع دوال المؤقتات
            if hasattr(module, 'timer_functions'):
                self.timer_functions.extend(module.timer_functions)
            
            self.plugins[plugin_name] = module
            return True
            
        except Exception as e:
            print(f"❌ خطأ في تحميل البلجن {plugin_name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_commands(self):
        """الحصول على جميع الأوامر المدمجة"""
        return self.commands
    
    def get_presence_handlers(self):
        """الحصول على معالجات الحضور"""
        return self.presence_handlers
    
    def get_message_handlers(self):
        """الحصول على معالجات الرسائل"""
        return self.message_handlers
    
    def get_iq_handlers(self):
        """الحصول على معالجات IQ"""
        return self.iq_handlers
    
    def get_timer_functions(self):
        """الحصول على دوال المؤقتات"""
        return self.timer_functions

# إنشاء نسخة من نظام البلاجنات
plugin_system = PluginSystem()
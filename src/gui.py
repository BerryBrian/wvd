import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import logging
from script import *
from auto_updater import *
from utils import *

############################################
class ConfigPanelApp(tk.Toplevel):
    def __init__(self, master_controller, version, msg_queue):
        self.URL = "https://github.com/arnold2957/wvd"

        # UI-visible title / intro (safe to translate)
        self.TITLE = f"WvDAS Wizardry Daphne Auto-Farm v{version} @Dellyla(Bilibili)"
        self.INTRODUCTION = f"Having issues? Visit:\n{self.URL}\nOr join QQ group: 922497356."

        RegisterQueueHandler()
        StartLogListener()

        super().__init__(master_controller)
        self.controller = master_controller
        self.msg_queue = msg_queue
        self.geometry('550x728')
        
        self.title(self.TITLE)

        self.adb_active = False

        # Exit whole program when closing UI
        self.protocol("WM_DELETE_WINDOW", self.controller.destroy)

        # --- Quest state ---
        self.quest_active = False

        # --- ttk Style ---
        self.style = ttk.Style()
        self.style.configure("custom.TCheckbutton")
        self.style.map("Custom.TCheckbutton",
            foreground=[("disabled selected", "#8CB7DF"),("disabled", "#A0A0A0"), ("selected", "#196FBF")])
        self.style.configure("BoldFont.TCheckbutton", font=("微软雅黑", 9,"bold"))
        self.style.configure("LargeFont.TCheckbutton", font=("微软雅黑", 12,"bold"))

        # --- UI Variables ---
        self.config = LoadConfigFromFile()
        for attr_name, var_type, var_config_name, var_default_value in CONFIG_VAR_LIST:
            if issubclass(var_type, tk.Variable):
                setattr(self, attr_name, var_type(value = self.config.get(var_config_name,var_default_value)))
            else:
                setattr(self, attr_name, var_type(self.config.get(var_config_name,var_default_value)))
        
        for btn,_,spellskillList,_,_ in SPELLSEKILL_TABLE:
            for item in spellskillList:
                if item not in self._spell_skill_config_internal:
                    setattr(self,f"{btn}_var",tk.BooleanVar(value = False))
                    break
                setattr(self,f"{btn}_var",tk.BooleanVar(value = True))             

        self.create_widgets()
        self.update_system_auto_combat()
        self.update_active_rest_state() # init inn-rest entry
        
        logger.info("**********************************")
        logger.info(f"Current version: {version}")
        logger.info(self.INTRODUCTION, extra={"summary": True})
        logger.info("**********************************")
        
        if self.last_version.g_

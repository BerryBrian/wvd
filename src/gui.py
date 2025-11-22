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
        
        if self.last_version.get() != version:
            ShowChangesLogWindow()
            self.last_version.set(version)
            self.save_config()

    def save_config(self):
        def standardize_karma_input():
          if self.karma_adjust_var.get().isdigit():
              valuestr = self.karma_adjust_var.get()
              self.karma_adjust_var.set('+' + valuestr)
        standardize_karma_input()

        emu_path = self.emu_path_var.get()
        emu_path = emu_path.replace("HD-Adb.exe", "HD-Player.exe")
        self.emu_path_var.set(emu_path)

        for attr_name, var_type, var_config_name, _ in CONFIG_VAR_LIST:
            if issubclass(var_type, tk.Variable):
                self.config[var_config_name] = getattr(self, attr_name).get()
        if self.system_auto_combat_var.get():
            self.config["_SPELLSKILLCONFIG"] = []
        else:
            self.config["_SPELLSKILLCONFIG"] = [s for s in ALL_SKILLS if s in list(set(self._spell_skill_config_internal))]

        if self.farm_target_text_var.get() in DUNGEON_TARGETS:
            self.farm_target_var.set(DUNGEON_TARGETS[self.farm_target_text_var.get()])
        else:
            self.farm_target_var.set(None)
        
        SaveConfigToFile(self.config)

    def updata_config(self):
        config = LoadConfigFromFile()
        if '_KARMAADJUST' in config:
            self.karma_adjust_var.set(config['_KARMAADJUST'])

    def create_widgets(self):
        scrolled_text_formatter = logging.Formatter('%(message)s')
        self.log_display = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, state=tk.DISABLED, bg='#ffffff',
            bd=2, relief=tk.FLAT, width=34, height=30
        )
        self.log_display.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrolled_text_handler = ScrolledTextHandler(self.log_display)
        self.scrolled_text_handler.setLevel(logging.INFO)
        self.scrolled_text_handler.setFormatter(scrolled_text_formatter)
        logger.addHandler(self.scrolled_text_handler)

        self.summary_log_display = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, state=tk.DISABLED, bg="#C6DBF4",
            bd=2, width=34,
        )
        self.summary_log_display.grid(row=1, column=1, pady=5)
        self.summary_text_handler = ScrolledTextHandler(self.summary_log_display)
        self.summary_text_handler.setLevel(logging.INFO)
        self.summary_text_handler.setFormatter(scrolled_text_formatter)
        self.summary_text_handler.addFilter(SummaryLogFilter())
        original_emit = self.summary_text_handler.emit
        def new_emit(record):
            self.summary_log_display.configure(state='normal')
            self.summary_log_display.delete(1.0, tk.END)
            self.summary_log_display.configure(state='disabled')
            original_emit(record)
        self.summary_text_handler.emit = new_emit
        logger.addHandler(self.summary_text_handler)

        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- ADB / Emulator setup ---
        row_counter = 0
        frame_row = ttk.Frame(self.main_frame)
        frame_row.grid(row=row_counter, column=0, sticky="ew", pady=5)
        self.adb_status_label = ttk.Label(frame_row)
        self.adb_status_label.grid(row=0, column=0)

        adb_entry = ttk.Entry(frame_row, textvariable=self.emu_path_var)
        adb_entry.grid_remove()

        def selectADB_PATH():
            path = filedialog.askopenfilename(
                title="Select ADB executable",
                filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
            )
            if path:
                self.emu_path_var.set(path)
                self.save_config()

        self.adb_path_change_button = ttk.Button(
            frame_row,
            text="Change",
            command=selectADB_PATH,
            width=5,
        )
        self.adb_path_change_button.grid(row=0, column=1)

        def update_adb_status(*args):
            if self.emu_path_var.get():
                self.adb_status_label.config(text="Emulator set", foreground="green")
            else:
                self.adb_status_label.config(text="Emulator not set", foreground="red")
        
        self.emu_path_var.trace_add("write", lambda *args: update_adb_status())
        update_adb_status()

        ttk.Label(frame_row, text="Port:").grid(row=0, column=2, sticky=tk.W, pady=5)
        vcmd_non_neg = self.register(lambda x: ((x=="") or (x.isdigit())))
        self.adb_port_entry = ttk.Entry(
            frame_row,
            textvariable=self.adb_port_var,
            validate="key",
            validatecommand=(vcmd_non_neg, '%P'),
            width=5
        )
        self.adb_port_entry.grid(row=0, column=3)
        self.button_save_adb_port = ttk.Button(
            frame_row,
            text="Save",
            command=self.save_config,
            width=5
        )
        self.button_save_adb_port.grid(row=0, column=4)

        # Separator
        row_counter += 1
        ttk.Separator(self.main_frame, orient='horizontal').grid(
            row=row_counter, column=0, columnspan=3, sticky='ew', pady=10
        )

        # --- Dungeon target ---
        row_counter += 1
        frame_row = ttk.Frame(self.main_frame)
        frame_row.grid(row=row_counter, column=0, sticky="ew", pady=5)
        ttk.Label(frame_row, text="Dungeon target:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.farm_target_combo = ttk.Combobox(
            frame_row, textvariable=self.farm_target_text_var,
            values=list(DUNGEON_TARGETS.keys()), state="readonly"
        )
        self.farm_target_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        self.farm_target_combo.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        # --- Chest opening settings ---
        row_counter += 1
        frame_row = ttk.Frame(self.main_frame)
        frame_row.grid(row=row_counter, column=0, sticky="ew", pady=5)
        self.random_chest_check = ttk.Checkbutton(
            frame_row,
            text="Smart chest opening (Beta)",
            variable=self.randomly_open_chest_var,
            command=self.save_config,
            style="Custom.TCheckbutton"
        )
        self.random_chest_check.grid(row=0, column=0, sticky=tk.W, pady=5)

        ttk.Label(frame_row, text="| Chest opener:").grid(row=0, column=1, sticky=tk.W, pady=5)

        # INTERNAL mapping left unchanged (questionable)
        self.open_chest_mapping = {
            0:"随机",
            1:"左上",
            2:"中上",
            3:"右上",
            4:"左下",
            5:"中下",
            6:"右下",
        }

        # Show Chinese direction labels in UI (Option A)
        self.who_will_open_text_var = tk.StringVar(
            value=self.open_chest_mapping[self.who_will_open_it_var.get()]
        )

        self.who_will_open_combobox = ttk.Combobox(
            frame_row,
            textvariable=self.who_will_open_text_var,
            values=list(self.open_chest_mapping.values()),
            state="readonly",
            width=4
        )
        self.who_will_open_combobox.grid(row=0, column=2, sticky=tk.W, pady=5)

        def handle_open_chest_selection(event=None):
            open_chest_reverse_mapping = {v: k for k, v in self.open_chest_mapping.items()}
            self.who_will_open_it_var.set(
                open_chest_reverse_mapping[self.who_will_open_text_var.get()]
            )
            self.save_config()

        self.who_will_open_combobox.bind("<<ComboboxSelected>>", handle_open_chest_selection)

        # --- Skip recovery ---
        row_counter += 1
        row_recover = tk.Frame(self.main_frame)
        row_recover.grid(row=row_counter, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.skip_recover_check = ttk.Checkbutton(
            row_recover,
            text="Skip post-battle recovery",
            variable=self.skip_recover_var,
            command=self.save_config,
            style="Custom.TCheckbutton"
        )
        self.skip_recover_check.grid(row=0, column=0)

        self.skip_chest_recover_check = ttk.Checkbutton(
            row_recover,
            text="Skip recovery after opening chests",
            variable=self.skip_chest_recover_var,
            command=self.save_config,
            style="Custom.TCheckbutton"
        )
        self.skip_chest_recover_check.grid(row=0, column=1)

        # --- Inn rest settings ---
        row_counter += 1
        frame_row = ttk.Frame(self.main_frame)
        frame_row.grid(row=row_counter, column=0, sticky="ew", pady=5)

        def checkcommand():
            self.update_active_rest_state()
            self.save_config()

        self.active_rest_check = ttk.Checkbutton(
            frame_row,
            variable=self.active_rest_var,
            text="Enable inn resting",
            command=checkcommand,
            style="Custom.TCheckbutton"
        )
        self.active_rest_check.grid(row=0, column=0)

        ttk.Label(frame_row, text=" | Interval:").grid(row=0, column=1, sticky=tk.W, pady=5)
        self.rest_intervel_entry = ttk.Entry(
            frame_row,
            textvariable=self.rest_intervel_var,
            validate="key",
            validatecommand=(vcmd_non_neg, '%P'),
            width=5
        )
        self.rest_intervel_entry.grid(row=0, column=2)

        self.button_save_rest_intervel = ttk.Button(
            frame_row,
            text="Save",
            command=self.save_config,
            width=4
        )
        self.button_save_rest_intervel.grid(row=0, column=3)

        # --- Karma settings ---
        row_counter += 1
        frame_row = ttk.Frame(self.main_frame)
        frame_row.grid(row=row_counter, column=0, sticky="ew", pady=5)
        ttk.Label(frame_row, text="Karma:").grid(row=0, column=0, sticky=tk.W, pady=5)

        # INTERNAL mapping left unchanged (questionable)
        self.karma_adjust_mapping = {
            "维持现状": "+0",
            "恶→中立,中立→善": "+17",
            "善→中立,中立→恶": "-17",
        }

        times = int(self.karma_adjust_var.get())
        if times == 0:
            self.karma_adjust_text_var = tk.StringVar(value="维持现状")
        elif times > 0:
            self.karma_adjust_text_var = tk.StringVar(value="恶→中立,中立→善")
        else:
            self.karma_adjust_text_var = tk.StringVar(value="善→中立,中立→恶")

        # Keep Chinese options shown (safe)
        self.karma_adjust_combobox = ttk.Combobox(
            frame_row,
            textvariable=self.karma_adjust_text_var,
            values=list(self.karma_adjust_mapping.keys()),
            state="readonly",
            width=14
        )
        self.karma_adjust_combobox.grid(row=0, column=1, sticky=tk.W, pady=5)

        def handle_karma_adjust_selection(event=None):
            karma_adjust_left = int(self.karma_adjust_var.get())
            karma_adjust_want = int(self.karma_adjust_mapping[self.karma_adjust_text_var.get()])
            if (karma_adjust_left == 0 and karma_adjust_want == 0) or (karma_adjust_left * karma_adjust_want > 0):
                return
            self.karma_adjust_var.set(self.karma_adjust_mapping[self.karma_adjust_text_var.get()])
            self.save_config()

        self.karma_adjust_combobox.bind("<<ComboboxSelected>>", handle_karma_adjust_selection)

        ttk.Label(frame_row, text="Remaining:").grid(row=0, column=2, sticky=tk.W, pady=5)
        ttk.Label(frame_row, textvariable=self.karma_adjust_var).grid(row=0, column=3, sticky=tk.W, pady=5)
        ttk.Label(frame_row, text="pts").grid(row=0, column=4, sticky=tk.W, pady=5)

        # Separator
        row_counter += 1
        ttk.Separator(self.main_frame, orient='horizontal').grid(
            row=row_counter, column=0, columnspan=3, sticky='ew', pady=10
        )

        # --- System auto-combat ---
        row_counter += 1
        self.system_auto_check = ttk.Checkbutton(
            self.main_frame,
            text="Enable auto-combat",
            variable=self.system_auto_combat_var,
            command=self.update_system_auto_combat,
            style="LargeFont.TCheckbutton"
        )
        self.system_auto_check.grid(row=row_counter, column=0, columnspan=2, sticky=tk.W, pady=5)

        def aoe_once_command():
            if self.aoe_once_var.get():
                if self.btn_enable_full_aoe_var.get() != True:
                    self.btn_enable_full_aoe.invoke()
                if self.btn_enable_secret_aoe_var.get() != True:
                    self.btn_enable_secret_aoe.invoke()
            self.update_change_aoe_once_check()
            self.save_config()

        row_counter += 1
        self.aoe_once_check = ttk.Checkbutton(
            self.main_frame,
            text="Only cast full-party AOE once per battle",
            variable=self.aoe_once_var,
            command=aoe_once_command,
            style="BoldFont.TCheckbutton"
        )
        self.aoe_once_check.grid(row=row_counter, column=0, columnspan=2, sticky=tk.W, pady=5)

        row_counter += 1
        self.auto_after_aoe_check = ttk.Checkbutton(
            self.main_frame,
            text="Enable auto-combat after AOE",
            variable=self.auto_after_aoe_var,
            command=self.save_config,
            style="BoldFont.TCheckbutton"
        )
        self.auto_after_aoe_check.grid(row=row_counter, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Skills buttons (buttonText is internal; leave as-is)
        row_counter += 1
        self.skills_button_frame = ttk.Frame(self.main_frame)
        self.skills_button_frame.grid(row=row_counter, column=0, columnspan=2, sticky=tk.W)
        for buttonName, buttonText, buttonSpell, row, col in SPELLSEKILL_TABLE:
            setattr(self, buttonName, ttk.Checkbutton(
                self.skills_button_frame,
                text=f"Enable {buttonText}",
                variable=getattr(self, f"{buttonName}_var"),
                command=lambda spell=buttonSpell, btnN=buttonName, btnT=buttonText: self.update_spell_config(spell, btnN, btnT),
                style="Custom.TCheckbutton"
            ))
            getattr(self, buttonName).grid(row=row, column=col, padx=2, pady=2)

        # Layout config
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        start_frame = ttk.Frame(self)
        start_frame.grid(row=1, column=0, sticky="nsew")
        start_frame.columnconfigure(0, weight=1)
        start_frame.rowconfigure(1, weight=1)

        ttk.Separator(start_frame, orient='horizontal').grid(row=0, column=0, columnspan=3, sticky="ew", padx=10)

        button_frame = ttk.Frame(start_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=5, sticky="nsew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        ttk.Label(button_frame, text="", anchor='center').grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        ttk.Label(button_frame, text="", anchor='center').grid(row=0, column=2, sticky='nsew', padx=5, pady=5)

        s = ttk.Style()
        s.configure('start.TButton', font=('微软雅黑', 15), padding=(0,5))

        def btn_command():
            self.save_config()
            self.toggle_start_stop()

        self.start_stop_btn = ttk.Button(
            button_frame,
            text="Start Script!",
            command=btn_command,
            style='start.TButton',
        )
        self.start_stop_btn.grid(row=0, column=1, sticky='nsew', padx=5, pady=26)

        # Separator
        row_counter += 1
        self.advance_sep = ttk.Separator(self.main_frame, orient='horizontal')
        self.advance_sep.grid(row=row_counter, column=0, columnspan=3, sticky='ew', pady=10)

        # --- Advanced options ---
        row_counter += 1
        frame_lux_rest = ttk.Frame(self.main_frame)
        frame_lux_rest.grid(row=row_counter, column=0, sticky="ew", pady=5)
        self.active_royalsuite_rest = ttk.Checkbutton(
            frame_lux_rest,
            variable=self.active_royalsuite_rest_var,
            text="Use royal suite",
            command=checkcommand,
            style="Custom.TCheckbutton"
        )
        self.active_royalsuite_rest.grid(row=0, column=0)

        row_counter += 1
        frame_row = ttk.Frame(self.main_frame)
        frame_row.grid(row=row_counter, column=0, sticky="ew", pady=5)
        self.active_triumph = ttk.Checkbutton(
            frame_row,
            variable=self.active_triumph_var,
            text='Jump to "Triumph" (requires Triumph unlocked)',
            command=checkcommand,
            style="Custom.TCheckbutton"
        )
        self.active_triumph.grid(row=0, column=0)

        row_counter += 1
        frame_row = ttk.Frame(self.main_frame)
        frame_row.grid(row=row_counter, column=0, sticky="ew", pady=5)
        self.active_csc = ttk.Checkbutton(
            frame_row,
            variable=self.active_csc_var,
            text="Try karma adjustment",
            command=checkcommand,
            style="Custom.TCheckbutton"
        )
        self.active_csc.grid(row=0, column=0)

        # Separator
        row_counter += 1
        self.update_sep = ttk.Separator(self.main_frame, orient='horizontal')
        self.update_sep.grid(row=row_counter, column=0, columnspan=3, sticky='ew', pady=10)

        # --- Update controls ---
        row_counter += 1
        frame_row_update = tk.Frame(self.main_frame)
        frame_row_update.grid(row=row_counter, column=0, sticky=tk.W)

        self.find_update = ttk.Label(frame_row_update, text="New version found:", foreground="red")
        self.find_update.grid(row=0, column=0, sticky=tk.W)

        self.update_text = ttk.Label(frame_row_update, textvariable=self.latest_version, foreground="red")
        self.update_text.grid(row=0, column=1, sticky=tk.W)

        self.button_auto_download = ttk.Button(
            frame_row_update,
            text="Auto download",
            width=10
        )
        self.button_auto_download.grid(row=0, column=2, sticky=tk.W, padx=5)

        def open_url():
            url = os.path.join(self.URL, "releases")
            if sys.platform == "win32":
                os.startfile(url)
            elif sys.platform == "darwin":
                os.system(f"open {url}")
            else:
                os.system(f"xdg-open {url}")

        self.button_manual_download = ttk.Button(
            frame_row_update,
            text="Download latest manually",
            command=open_url,
            width=20
        )
        self.button_manual_download.grid(row=0, column=3, sticky=tk.W)

        self.update_sep.grid_remove()
        self.find_update.grid_remove()
        self.update_text.grid_remove()
        self.button_auto_download.grid_remove()
        self.button_manual_download.grid_remove()

    def update_active_rest_state(self):
        if self.active_rest_var.get():
            self.rest_intervel_entry.config(state="normal")
            self.button_save_rest_intervel.config(state="normal")
        else:
            self.rest_intervel_entry.config(state="disable")
            self.button_save_rest_intervel.config(state="disable")

    def update_change_aoe_once_check(self):
        if self.aoe_once_var.get() == False:
            self.auto_after_aoe_var.set(False)
            self.auto_after_aoe_check.config(state="disabled")
        if self.aoe_once_var.get():
            self.auto_after_aoe_check.config(state="normal")

    def update_system_auto_combat(self):
        is_system_auto = self.system_auto_combat_var.get()

        if is_system_auto:
            self._spell_skill_config_internal = ["systemAuto"]
        else:
            if self._spell_skill_config_internal == ["systemAuto"]:
                self._spell_skill_config_internal = []
                for buttonName, buttonText, buttonSpell, row, col in SPELLSEKILL_TABLE:
                    if getattr(self, f"{buttonName}_var").get():
                        self._spell_skill_config_internal += buttonSpell
        
        button_state = tk.DISABLED if is_system_auto else tk.NORMAL
        for buttonName, _, _, _, _ in SPELLSEKILL_TABLE:
            getattr(self, buttonName).config(state=button_state)
        self.aoe_once_check.config(state=button_state)
        if is_system_auto:
            self.auto_after_aoe_check.config(state=button_state)
        else:
            self.update_change_aoe_once_check()
        
        self.save_config()

    def update_spell_config(self, skills_to_process, buttonName, buttonText):
        if self.system_auto_combat_var.get():
            return

        skills_to_process_set = set(skills_to_process)

        if buttonName == "btn_enable_all":
            if getattr(self, f"{buttonName}_var").get():
                self._spell_skill_config_internal = list(skills_to_process_set)
                logger.info(f"All skills enabled: {self._spell_skill_config_internal}")
                for btn, _, _, _, _ in SPELLSEKILL_TABLE:
                    if btn != buttonName:
                        getattr(self, f"{btn}_var").set(True)
            else:
                self._spell_skill_config_internal = []
                for btn, _, _, _, _ in SPELLSEKILL_TABLE:
                    if btn != buttonName:
                        getattr(self, f"{btn}_var").set(False)
                logger.info("All skills disabled.")
        else:
            if getattr(self, f"{buttonName}_var").get():
                for skill in skills_to_process:
                    if skill not in self._spell_skill_config_internal:
                        self._spell_skill_config_internal.append(skill)
                logger.info(f"{buttonText} enabled. Current skills: {self._spell_skill_config_internal}")
            else:
                self._spell_skill_config_internal = [s for s in self._spell_skill_config_internal if s not in skills_to_process_set]
                logger.info(f"{buttonText} disabled. Current skills: {self._spell_skill_config_internal}")

        self._spell_skill_config_internal = list(dict.fromkeys(self._spell_skill_config_internal))
        self.save_config()

    def set_controls_state(self, state):
        self.button_and_entry = [
            self.adb_path_change_button,
            self.random_chest_check,
            self.who_will_open_combobox,
            self.system_auto_check,
            self.aoe_once_check,
            self.auto_after_aoe_check,
            self.skip_recover_check,
            self.skip_chest_recover_check,
            self.active_rest_check,
            self.rest_intervel_entry,
            self.button_save_rest_intervel,
            self.karma_adjust_combobox,
            self.adb_port_entry,
            self.active_triumph,
            self.active_royalsuite_rest,
            self.button_save_adb_port,
            self.active_csc
        ]

        if state == tk.DISABLED:
            self.farm_target_combo.configure(state="disabled")
            for widget in self.button_and_entry:
                widget.configure(state="disabled")
        else:
            self.farm_target_combo.configure(state="readonly")
            for widget in self.button_and_entry:
                widget.configure(state="normal")
            self.update_active_rest_state()
            self.update_change_aoe_once_check()

        if not self.system_auto_combat_var.get():
            widgets = [*[getattr(self, buttonName) for buttonName, _, _, _, _ in SPELLSEKILL_TABLE]]
            for widget in widgets:
                if isinstance(widget, ttk.Widget):
                    widget.state([state.lower()] if state != tk.NORMAL else ['!disabled'])

    def toggle_start_stop(self):
        if not self.quest_active:
            self.start_stop_btn.config(text="Stop")
            self.set_controls_state(tk.DISABLED)
            setting = FarmConfig()
            config = LoadConfigFromFile()
            for attr_name, var_type, var_config_name, var_default_value in CONFIG_VAR_LIST:
                setattr(setting, var_config_name, config[var_config_name])
            setting._FINISHINGCALLBACK = self.finishingcallback
            self.msg_queue.put(('start_quest', setting))
            self.quest_active = True
        else:
            self.msg_queue.put(('stop_quest', None))

    def finishingcallback(self):
        logger.info("Stopped.")
        self.start_stop_btn.config(text="Start Script!")
        self.set_controls_state(tk.NORMAL)
        self.updata_config()
        self.quest_active = False

    def turn_to_7000G(self):
        self.summary_log_display.config(bg="#F4C6DB")
        self.main_frame.grid_remove()
        summary = self.summary_log_display.get("1.0", "end-1c")
        if self.INTRODUCTION in summary:
            summary = "Hmm... looks like no dungeon runs were completed."
        text = (
            "Your party has used up all the Revival Flames.\n"
            "Before that happened, your team achieved:\n\n"
            f"{summary}\n\n"
            "But it's okay — you can still ask the princess for money.\n\n"
            "Praise the Princess!\n"
        )
        turn_to_7000G_label = ttk.Label(self, text=text)
        turn_to_7000G_label.grid(row=0, column=0)

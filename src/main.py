from gui import *
import argparse

__version__ = '1.9.212' 
OWNER = "arnold2957"
REPO = "wvd"

class AppController(tk.Tk):
    def __init__(self, headless, config_path):
        super().__init__()
        self.withdraw()
        self.msg_queue = queue.Queue()
        self.main_window = None
        if not headless:
            if not self.main_window:
                self.main_window = ConfigPanelApp(
                    self,
                    __version__,
                    self.msg_queue
                )
        else:
            HeadlessActive(config_path, self.msg_queue)
            
        self.quest_threading = None
        self.quest_setting = None

        self.is_checking_for_update = False 
        self.updater = AutoUpdater(
            msg_queue=self.msg_queue,
            github_user=OWNER,
            github_repo=REPO,
            current_version=__version__
        )
        self.schedule_periodic_update_check()
        self.check_queue()

    def run_in_thread(self, target_func, *args):
        thread = threading.Thread(target=target_func, args=args, daemon=True)
        thread.start()

    def schedule_periodic_update_check(self):
        # If not already checking/downloading, start a new check
        if not self.is_checking_for_update:
            # print("Scheduler: starting hourly background update check...")
            self.is_checking_for_update = True
            self.run_in_thread(self.updater.check_for_updates)
            self.is_checking_for_update = False
        else:
            # print("Scheduler: previous check/download still running; skipping.")
            None
        self.after(3600000, self.schedule_periodic_update_check)

    def check_queue(self):
        """Handle messages from AutoUpdater and other services"""
        try:
            message = self.msg_queue.get_nowait()
            command, value = message
            
            # --- Core update/quest logic ---
            match command:
                case 'start_quest':
                    self.quest_setting = value                    
                    self.quest_setting._MSGQUEUE = self.msg_queue
                    self.quest_setting._FORCESTOPING = Event()
                    Farm = Factory()
                    self.quest_threading = Thread(target=Farm, args=(self.quest_setting,))
                    self.quest_threading.start()
                    logger.info(f'Starting task "{self.quest_setting._FARMTARGET_TEXT}"...')

                case 'stop_quest':
                    logger.info('Stopping task...')
                    if hasattr(self, 'quest_threading') and self.quest_threading.is_alive():
                        if hasattr(self.quest_setting, '_FORCESTOPING'):
                            self.quest_setting._FORCESTOPING.set()
                
                case 'turn_to_7000G':
                    logger.info('Starting money run...')
                    self.quest_setting._FARMTARGET = "7000G"
                    self.quest_setting._COUNTERDUNG = 0
                    while 1:
                        if not self.quest_threading.is_alive():
                            Farm = Factory()
                            self.quest_threading = Thread(target=Farm, args=(self.quest_setting,))
                            self.quest_threading.start()
                            break
                    if self.main_window:
                        self.main_window.turn_to_7000G()

                case 'update_available':
                    update_data = value
                    version = update_data['version']
                    if self.main_window:
                        self.main_window.find_update.grid()
                        self.main_window.update_text.grid()
                        self.main_window.latest_version.set(version)
                        self.main_window.button_auto_download.grid()
                        self.main_window.button_manual_download.grid()
                        self.main_window.update_sep.grid()
                        self.main_window.save_config()
                        width, height = map(int, self.main_window.geometry().split('+')[0].split('x'))
                        self.main_window.geometry(f'{width}x{height+50}')

                        self.main_window.button_auto_download.config(
                            command=lambda: self.run_in_thread(self.updater.download)
                        )

                case 'download_started':
                    if not hasattr(self, 'progress_window') or not self.progress_window.winfo_exists():
                        self.progress_window = Progressbar(
                            self.main_window,
                            title="Downloading...",
                            max_size=value
                        )

                case 'progress':
                    if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
                        self.progress_window.update_progress(value)
                        self.update()
                        None

                case 'download_complete':
                    if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
                        self.progress_window.destroy()

                case 'error':
                    if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
                        self.progress_window.destroy()
                    messagebox.showerror("Error", value, parent=self.main_window)

                case 'restart_ready':
                    script_path = value
                    messagebox.showinfo(
                        "Update Complete",
                        "The new version is ready. The app will restart now!",
                        parent=self.main_window
                    )
                    
                    if sys.platform == "win32":
                        subprocess.Popen([script_path], shell=True)
                    else:
                        os.system(script_path)
                    
                    self.destroy()
                    
                case 'no_update_found':
                    print("UI: No updates found.")

        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

def parse_args():
    """Parse command-line args"""
    parser = argparse.ArgumentParser(description='WvDAS command-line options')
    
    parser.add_argument(
        '-headless', 
        '--headless', 
        action='store_true',
        help='Run in headless mode'
    )
    
    parser.add_argument(
        '-config', 
        '--config', 
        type=str,
        default=None,
        help='Path to config file (e.g., c:/config.json)'
    )
    
    return parser.parse_args()

def main():
    args = parse_args()

    controller = AppController(args.headless, args.config)
    controller.mainloop()

def HeadlessActive(config_path, msg_queue):
    RegisterConsoleHandler()
    RegisterQueueHandler()
    StartLogListener()

    setting = FarmConfig()
    config = LoadConfigFromFile(config_path)
    for _, _, var_config_name, _ in CONFIG_VAR_LIST:
        setattr(setting, var_config_name, config[var_config_name])
    msg_queue.put(('start_quest', setting))

    # User-facing console log only
    logger.info(f"WvDAS Wizardry Daphne Auto-Farm v{__version__} @Dellyla(Bilibili)")

if __name__ == "__main__":
    main()

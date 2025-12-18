import customtkinter as ctk
import threading
import sys
import os
import sqlite3
import asyncio
import aiohttp
from tkinter import messagebox
from dotenv import load_dotenv

# Import the bot starter
from main import start_bot_thread

# Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DB_NAME = "stalker_data.db"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("RBXStalker V2")
        self.geometry("1000x650")
        self.minsize(900, 600)

        # Check for .env file
        if not os.path.exists(".env"):
            self.show_setup_screen()
        else:
            # Load env vars immediately if they exist
            load_dotenv()
            self.build_dashboard()
            # Start Bot
            self.bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
            self.bot_thread.start()

    # ==========================
    #      FIRST TIME SETUP
    # ==========================
    def show_setup_screen(self):
        self.setup_frame = ctk.CTkFrame(self)
        self.setup_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        ctk.CTkLabel(self.setup_frame, text="First Time Setup", font=("Segoe UI", 32, "bold")).pack(pady=(40, 10))
        ctk.CTkLabel(self.setup_frame, text="Please configure your bot to continue.", text_color="gray").pack(pady=(0, 30))

        # 1. Discord Token
        ctk.CTkLabel(self.setup_frame, text="Discord Bot Token (Required)", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=100)
        self.entry_token = ctk.CTkEntry(self.setup_frame, placeholder_text="Paste your bot token here...", width=600)
        self.entry_token.pack(pady=(5, 20))

        # 2. Roblox Cookie
        ctk.CTkLabel(self.setup_frame, text="Roblox Security Cookie (Optional)", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=100)
        
        # Instructions Frame
        inst_frame = ctk.CTkFrame(self.setup_frame, fg_color="#2b2b2b")
        inst_frame.pack(pady=(0, 10), padx=100, fill="x")
        
        inst_text = (
            "How to get your .ROBLOSECURITY cookie:\n"
            "1. Open a new Incognito/Private browser window and log in to Roblox.\n"
            "2. Press F12 (Developer Tools) and go to the 'Application' (Chrome) or 'Storage' (Firefox) tab.\n"
            "3. Expand 'Cookies' on the left, click 'https://www.roblox.com'.\n"
            "4. Find '.ROBLOSECURITY', copy the long value, and paste it below."
        )
        ctk.CTkLabel(inst_frame, text=inst_text, justify="left", font=("Consolas", 11), text_color="#aaa").pack(padx=10, pady=10, anchor="w")

        self.entry_cookie = ctk.CTkEntry(self.setup_frame, placeholder_text="_|WARNING:-DO-NOT-SHARE-THIS.--...", width=600)
        self.entry_cookie.pack(pady=(5, 30))

        # Save Button
        ctk.CTkButton(self.setup_frame, text="Save Configuration & Start", width=200, height=50, 
                      font=("Segoe UI", 15, "bold"), command=self.save_setup).pack()

    def save_setup(self):
        token = self.entry_token.get().strip()
        cookie = self.entry_cookie.get().strip()

        if not token:
            messagebox.showerror("Error", "Discord Bot Token is required!")
            return

        # Write to .env file
        with open(".env", "w") as f:
            f.write(f"DISCORD_TOKEN={token}\n")
            if cookie:
                f.write(f"ROBLOSECURITY={cookie}\n")

        # Reload environment to pick up new vars
        load_dotenv(override=True)

        messagebox.showinfo("Success", "Configuration saved! Starting dashboard...")
        
        # Destroy setup and load dashboard
        self.setup_frame.destroy()
        self.build_dashboard()
        
        # Start Bot
        self.bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
        self.bot_thread.start()


    # ==========================
    #       MAIN DASHBOARD
    # ==========================
    def build_dashboard(self):
        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="RBXStalker", font=ctk.CTkFont(size=26, weight="bold", family="Segoe UI"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        self.version_label = ctk.CTkLabel(self.sidebar, text="System Online", text_color="#2ecc71", font=("Segoe UI", 12))
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 30))

        # Add User Section
        self.input_label = ctk.CTkLabel(self.sidebar, text="ADD TRACKING TARGET", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        self.input_label.grid(row=2, column=0, padx=20, pady=(10,5), sticky="w")

        self.entry_input = ctk.CTkEntry(self.sidebar, placeholder_text="Username or ID")
        self.entry_input.grid(row=3, column=0, padx=20, pady=(0, 10))
        
        self.add_btn = ctk.CTkButton(self.sidebar, text="+ Add User", command=self.start_add_process, fg_color="#3498db", hover_color="#2980b9", font=("Segoe UI", 13, "bold"))
        self.add_btn.grid(row=4, column=0, padx=20, pady=5)
        
        self.status_label = ctk.CTkLabel(self.sidebar, text="", font=("Segoe UI", 11))
        self.status_label.grid(row=5, column=0, padx=20, pady=5)

        # Settings Section
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=9, column=0, padx=20, pady=(200, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar, values=["Dark", "Light", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=10, column=0, padx=20, pady=(10, 20))

        # --- MAIN CONTENT ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Active Targets", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(self.header_frame, text="🔄 Force Refresh", width=100, command=lambda: self.load_users(force_rebuild=True), fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
        self.refresh_btn.pack(side="right")

        # Scrollable List
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_container, label_text="")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(1, weight=1) 

        self.user_rows = {}
        
        # Initial Load & Auto Refresh
        self.load_users(force_rebuild=True)
        self.auto_refresh()

    def get_db(self):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    # --- ADD USER LOGIC ---
    def start_add_process(self):
        user_input = self.entry_input.get()
        if not user_input: return
        
        self.add_btn.configure(state="disabled", text="Checking...")
        self.status_label.configure(text="Fetching API...", text_color="yellow")
        threading.Thread(target=self.fetch_and_add_user, args=(user_input,), daemon=True).start()

    def fetch_and_add_user(self, user_input):
        asyncio.run(self._async_fetch(user_input))

    async def _async_fetch(self, user_input):
        url = "https://users.roblox.com/v1/usernames/users"
        final_id = None
        final_name = None
        
        async with aiohttp.ClientSession() as session:
            if user_input.isdigit():
                async with session.get(f"https://users.roblox.com/v1/users/{user_input}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        final_id = data['id']
                        final_name = data['name']
            
            if not final_id:
                payload = {"usernames": [user_input], "excludeBannedUsers": True}
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data['data']:
                            final_id = data['data'][0]['id']
                            final_name = data['data'][0]['name']

        self.after(0, lambda: self.finalize_add(final_id, final_name))

    def finalize_add(self, uid, name):
        self.add_btn.configure(state="normal", text="+ Add User")
        
        if uid and name:
            try:
                conn = self.get_db()
                conn.execute("INSERT OR REPLACE INTO tracked_users (user_id, username, display_name, enabled, ping_mode) VALUES (?, ?, ?, 1, 'ping')", (uid, name, name))
                conn.execute("INSERT OR IGNORE INTO user_history (user_id) VALUES (?)", (uid,))
                conn.commit()
                conn.close()
                self.entry_input.delete(0, 'end')
                self.status_label.configure(text=f"Added: {name}", text_color="#2ecc71")
                self.load_users(force_rebuild=True)
            except Exception as e:
                self.status_label.configure(text="DB Error", text_color="red")
        else:
            self.status_label.configure(text="User Not Found", text_color="red")
            messagebox.showerror("Error", "Could not find user on Roblox.")

    # --- ACTIONS ---
    def remove_user(self, uid):
        if messagebox.askyesno("Confirm", f"Stop tracking ID {uid}?"):
            conn = self.get_db()
            conn.execute("DELETE FROM tracked_users WHERE user_id = ?", (uid,))
            conn.commit()
            conn.close()
            if uid in self.user_rows:
                for w in self.user_rows[uid].values(): w.destroy()
                del self.user_rows[uid]

    def toggle_priority(self, uid, current_val):
        new_val = 1 if current_val == 0 else 0
        conn = self.get_db()
        conn.execute("UPDATE tracked_users SET priority = ? WHERE user_id = ?", (new_val, uid))
        conn.commit()
        conn.close()
        self.load_users()

    def toggle_ping(self, uid, current_mode):
        new_mode = "noping" if current_mode == "ping" else "ping"
        conn = self.get_db()
        conn.execute("UPDATE tracked_users SET ping_mode = ? WHERE user_id = ?", (new_mode, uid))
        conn.commit()
        conn.close()
        self.load_users()

    # --- REFRESH LOGIC ---
    def auto_refresh(self):
        self.load_users()
        self.after(2000, self.auto_refresh) 

    def load_users(self, force_rebuild=False):
        conn = self.get_db()
        try:
            users = conn.execute("SELECT * FROM tracked_users WHERE enabled=1").fetchall()
        except sqlite3.OperationalError:
            users = []
        conn.close()

        if force_rebuild:
            for widget in self.scroll_frame.winfo_children(): widget.destroy()
            self.user_rows = {}
            headers = ["ID", "Display Name", "Status", "Priority", "Alerts", "Actions"]
            for i, h in enumerate(headers):
                ctk.CTkLabel(self.scroll_frame, text=h, font=("Segoe UI", 12, "bold"), text_color="gray").grid(row=0, column=i, padx=10, pady=(0, 10), sticky="w")

        current_ids = [u['user_id'] for u in users]
        if not force_rebuild:
            for uid in list(self.user_rows.keys()):
                if uid not in current_ids:
                    for w in self.user_rows[uid].values(): w.destroy()
                    del self.user_rows[uid]

        for idx, u in enumerate(users):
            uid = u['user_id']
            r = idx + 1
            
            status_map = {0: "Offline", 1: "Online", 2: "In Game", 3: "Studio"}
            status_text = status_map.get(u['last_presence_type'], "Unknown")
            status_color = "#e74c3c" if u['last_presence_type'] == 0 else "#2ecc71" if u['last_presence_type'] == 1 else "#3498db" if u['last_presence_type'] == 2 else "#f39c12"

            p_text = "⚡ HIGH" if u['priority'] == 1 else "Normal"
            p_fg = "#f1c40f" if u['priority'] == 1 else "transparent"
            p_text_col = "black" if u['priority'] == 1 else "gray"
            
            ping_text = "🔔 Ping" if u['ping_mode'] == "ping" else "🔕 Silent"
            ping_fg = "#9b59b6" if u['ping_mode'] == "ping" else "transparent"

            if uid not in self.user_rows:
                self.user_rows[uid] = {}
                self.user_rows[uid]['id'] = ctk.CTkLabel(self.scroll_frame, text=str(uid), font=("Consolas", 12))
                self.user_rows[uid]['id'].grid(row=r, column=0, padx=10, pady=8, sticky="w")
                self.user_rows[uid]['name'] = ctk.CTkLabel(self.scroll_frame, text=u['display_name'], font=("Segoe UI", 13, "bold"))
                self.user_rows[uid]['name'].grid(row=r, column=1, padx=10, pady=8, sticky="w")
                self.user_rows[uid]['status'] = ctk.CTkLabel(self.scroll_frame, text=status_text, text_color=status_color, font=("Segoe UI", 12, "bold"))
                self.user_rows[uid]['status'].grid(row=r, column=2, padx=10, pady=8, sticky="w")
                self.user_rows[uid]['prio'] = ctk.CTkButton(self.scroll_frame, width=70, height=24, border_width=1, border_color="#555")
                self.user_rows[uid]['prio'].grid(row=r, column=3, padx=10, pady=8, sticky="w")
                self.user_rows[uid]['ping'] = ctk.CTkButton(self.scroll_frame, width=70, height=24, border_width=1, border_color="#9b59b6")
                self.user_rows[uid]['ping'].grid(row=r, column=4, padx=10, pady=8, sticky="w")
                self.user_rows[uid]['del'] = ctk.CTkButton(self.scroll_frame, text="Remove", width=60, height=24, fg_color="#c0392b", hover_color="#a93226", command=lambda i=uid: self.remove_user(i))
                self.user_rows[uid]['del'].grid(row=r, column=5, padx=10, pady=8, sticky="w")

            row = self.user_rows[uid]
            for widget in row.values(): widget.grid(row=r)
            row['status'].configure(text=status_text, text_color=status_color)
            row['prio'].configure(text=p_text, fg_color=p_fg, text_color=p_text_col, command=lambda i=uid, v=u['priority']: self.toggle_priority(i, v))
            row['ping'].configure(text=ping_text, fg_color=ping_fg, command=lambda i=uid, v=u['ping_mode']: self.toggle_ping(i, v))

if __name__ == "__main__":
    app = App()
    app.mainloop()
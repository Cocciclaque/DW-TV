import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    messagebox.showinfo("Saved", "Configuration saved successfully!")

class ConfigEditor(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding="10")
        self.root = root
        self.root.title("Config Editor")
        self.root.geometry("340x550")
        self.cfg = load_config()
        self.grid(sticky="nsew")
        self.create_widgets()
        self.populate_fields()

    def create_widgets(self):
        # General Settings Frame
        general_frame = ttk.LabelFrame(self, text="General Settings", padding=10)
        general_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        general_frame.columnconfigure(1, weight=1)

        ttk.Label(general_frame, text="Scroll Speed:").grid(row=0, column=0, sticky="e", pady=2)
        self.scroll_speed_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.scroll_speed_var, width=20).grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(general_frame, text="Refresh Interval (ms):").grid(row=1, column=0, sticky="e", pady=2)
        self.refresh_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.refresh_var, width=20).grid(row=1, column=1, sticky="w", pady=2)

        # Event Slugs Frame
        event_frame = ttk.LabelFrame(self, text="Event Slugs", padding=10)
        event_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        event_frame.columnconfigure(0, weight=1)

        self.event_listbox = tk.Listbox(event_frame, height=8)
        self.event_listbox.grid(row=0, column=0, sticky="nsew", pady=2)
        scrollbar = ttk.Scrollbar(event_frame, orient="vertical", command=self.event_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.event_listbox.config(yscrollcommand=scrollbar.set)

        event_btn_frame = ttk.Frame(event_frame)
        event_btn_frame.grid(row=0, column=2, sticky="ns", padx=5)
        ttk.Button(event_btn_frame, text="Add", command=self.add_event).pack(fill="x", pady=2)
        ttk.Button(event_btn_frame, text="Edit", command=self.edit_event).pack(fill="x", pady=2)
        ttk.Button(event_btn_frame, text="Remove", command=self.remove_event).pack(fill="x", pady=2)

        # Rotation Frame
        rotation_frame = ttk.LabelFrame(self, text="Rotation Settings", padding=10)
        rotation_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        rotation_frame.columnconfigure(1, weight=1)

        ttk.Label(rotation_frame, text="Enabled:").grid(row=0, column=0, sticky="e", pady=2)
        self.rotation_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(rotation_frame, variable=self.rotation_enabled_var).grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(rotation_frame, text="Interval (s):").grid(row=1, column=0, sticky="e", pady=2)
        self.rotation_interval_var = tk.StringVar()
        ttk.Entry(rotation_frame, textvariable=self.rotation_interval_var, width=20).grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(rotation_frame, text="Order:").grid(row=2, column=0, sticky="ne", pady=2)
        self.rotation_order_listbox = tk.Listbox(rotation_frame, height=6)
        self.rotation_order_listbox.grid(row=2, column=1, sticky="nsew", pady=2)
        rot_scrollbar = ttk.Scrollbar(rotation_frame, orient="vertical", command=self.rotation_order_listbox.yview)
        rot_scrollbar.grid(row=2, column=2, sticky="ns")
        self.rotation_order_listbox.config(yscrollcommand=rot_scrollbar.set)

        rot_btn_frame = ttk.Frame(rotation_frame)
        rot_btn_frame.grid(row=2, column=3, sticky="ns", padx=5)
        ttk.Button(rot_btn_frame, text="Add", command=self.add_rotation_order).pack(fill="x", pady=2)
        ttk.Button(rot_btn_frame, text="Remove", command=self.remove_rotation_order).pack(fill="x", pady=2)
        ttk.Button(rot_btn_frame, text="Up", command=lambda: self.move_rotation_order(-1)).pack(fill="x", pady=2)
        ttk.Button(rot_btn_frame, text="Down", command=lambda: self.move_rotation_order(1)).pack(fill="x", pady=2)

        # Save Button
        ttk.Button(self, text="Save Configuration", command=self.save).grid(row=3, column=0, pady=10)

        # Make everything expand nicely
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

    def populate_fields(self):
        self.scroll_speed_var.set(str(self.cfg.get("scrollSpeed", "")))
        self.refresh_var.set(str(self.cfg.get("refreshIntervalMs", "")))

        self.event_listbox.delete(0, tk.END)
        for slug, path in self.cfg.get("event_slugs", {}).items():
            self.event_listbox.insert(tk.END, f"{slug}: {path}")

        rotation = self.cfg.get("rotation", {})
        self.rotation_enabled_var.set(rotation.get("enabled", False))
        self.rotation_interval_var.set(str(rotation.get("intervalSeconds", "")))
        self.rotation_order_listbox.delete(0, tk.END)
        for item in rotation.get("order", []):
            self.rotation_order_listbox.insert(tk.END, item)

    # Event Slugs Functions
    def add_event(self):
        slug = simpledialog.askstring("Slug", "Enter event slug:")
        path = simpledialog.askstring("Path", "Enter event path:")
        if slug and path:
            self.event_listbox.insert(tk.END, f"{slug}: {path}")

    def edit_event(self):
        idx = self.event_listbox.curselection()
        if not idx:
            return
        idx = idx[0]
        current = self.event_listbox.get(idx)
        slug, path = current.split(": ", 1)
        new_slug = simpledialog.askstring("Slug", "Edit slug:", initialvalue=slug)
        new_path = simpledialog.askstring("Path", "Edit path:", initialvalue=path)
        if new_slug and new_path:
            self.event_listbox.delete(idx)
            self.event_listbox.insert(idx, f"{new_slug}: {new_path}")

    def remove_event(self):
        idx = self.event_listbox.curselection()
        if idx:
            self.event_listbox.delete(idx[0])

    # Rotation Order Functions
    def add_rotation_order(self):
        item = simpledialog.askstring("Rotation Item", "Enter event slug for rotation:")
        if item:
            self.rotation_order_listbox.insert(tk.END, item)

    def remove_rotation_order(self):
        idx = self.rotation_order_listbox.curselection()
        if idx:
            self.rotation_order_listbox.delete(idx[0])

    def move_rotation_order(self, direction):
        idx = self.rotation_order_listbox.curselection()
        if not idx:
            return
        idx = idx[0]
        new_idx = idx + direction
        if 0 <= new_idx < self.rotation_order_listbox.size():
            item = self.rotation_order_listbox.get(idx)
            self.rotation_order_listbox.delete(idx)
            self.rotation_order_listbox.insert(new_idx, item)
            self.rotation_order_listbox.select_set(new_idx)

    def save(self):
        try:
            cfg = {
                "scrollSpeed": float(self.scroll_speed_var.get()),
                "refreshIntervalMs": int(self.refresh_var.get()),
                "event_slugs": {},
                "rotation": {
                    "enabled": self.rotation_enabled_var.get(),
                    "intervalSeconds": int(self.rotation_interval_var.get()),
                    "order": list(self.rotation_order_listbox.get(0, tk.END))
                }
            }
            for item in self.event_listbox.get(0, tk.END):
                slug, path = item.split(": ", 1)
                cfg["event_slugs"][slug] = path
            save_config(cfg)
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigEditor(root)
    root.mainloop()

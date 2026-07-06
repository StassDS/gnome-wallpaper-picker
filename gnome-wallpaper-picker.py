#!/usr/bin/env python3
import os
import sys
import gi
from PIL import Image

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw, GLib, Gdk

# ПУТИ
WALLPAPER_DIR = "/СЮДА/ПУТЬ/К/ВАШИМ/ОБОЯМ"
CACHE_DIR = os.path.expanduser("~/.cache/gnome-wallpaper-picker")

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_thumbnail(full_path):
    filename = os.path.basename(full_path)
    thumb_path = os.path.join(CACHE_DIR, f"thumb_{filename}")
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        with Image.open(full_path) as img:
            w_percent = (250 / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((250, h_size), Image.Resampling.LANCZOS)
            img.save(thumb_path, "JPEG", quality=80)
        return thumb_path
    except Exception:
        return full_path

def clean_cache(valid_files):
    if os.path.exists(CACHE_DIR):
        cached_thumbs = os.listdir(CACHE_DIR)
        valid_thumbs = [f"thumb_{f}" for f in valid_files]
        for thumb in cached_thumbs:
            if thumb not in valid_thumbs:
                try:
                    os.remove(os.path.join(CACHE_DIR, thumb))
                except Exception:
                    pass

class NavbarApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='org.gnome.wallpaperpicker', flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.win = None

    def do_activate(self):
        if self.win:
            self.win.present()
            return

        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_title("Выбор обоев")
        self.win.set_default_size(850, 550)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(main_box)

        header = Adw.HeaderBar()
        main_box.append(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        main_box.append(scrolled)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_margin_top(15)
        self.flowbox.set_margin_bottom(15)
        self.flowbox.set_margin_start(15)
        self.flowbox.set_margin_end(15)
        self.flowbox.set_column_spacing(15)
        self.flowbox.set_row_spacing(15)
        scrolled.set_child(self.flowbox)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.win.add_controller(key_controller)

        self.win.present()
        GLib.idle_add(self.load_wallpapers)

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.win.close()
            self.win = None
            return True
        return False

    def load_wallpapers(self):
        if os.path.exists(WALLPAPER_DIR):
            valid_exts = ('.jpg', '.jpeg', '.png', '.webp')
            files = sorted([f for f in os.listdir(WALLPAPER_DIR) if f.lower().endswith(valid_exts)])
            
            clean_cache(files)
            
            for file in files:
                full_path = os.path.join(WALLPAPER_DIR, file)
                thumb_path = get_thumbnail(full_path)
                
                btn = Gtk.Button()
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                
                img = Gtk.Image.new_from_file(thumb_path)
                img.set_pixel_size(160)
                img.set_size_request(160, 100)
                
                lbl = Gtk.Label(label=file[:15] + '...' if len(file) > 15 else file)
                
                box.append(img)
                box.append(lbl)
                btn.set_child(box)
                
                btn.connect("clicked", self.on_click, full_path)
                self.flowbox.append(btn)
        else:
            self.flowbox.append(Gtk.Label(label=f"Папка не найдена: {WALLPAPER_DIR}"))
        
        return False

    def on_click(self, button, path):
        uri = f"file://{path}"
        settings = Gio.Settings.new("org.gnome.desktop.background")
        settings.set_string("picture-uri", uri)
        settings.set_string("picture-uri-dark", uri)
        self.win.close()
        self.win = None 

if __name__ == '__main__':
    app = NavbarApp()
    sys.exit(app.run(sys.argv))

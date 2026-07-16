#!/usr/bin/env python3
import os
import sys
import time
import gi
from PIL import Image

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw, GLib, Gdk

# ПУТИ
WALLPAPER_DIR = "/home/starbtf_arch/Изображения/wallpaper"
CACHE_DIR = os.path.expanduser("~/.cache/gnome-wallpaper-picker")

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_thumbnail(full_path):
    filename = os.path.basename(full_path)
    safe_name = full_path.replace("/", "_").strip("_")
    thumb_path = os.path.join(CACHE_DIR, f"thumb_{safe_name}")
    
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        with Image.open(full_path) as img:
            w_percent = (250 / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((250, h_size), Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(thumb_path, "JPEG", quality=80)
        return thumb_path
    except Exception as e:
        print(f"Ошибка создания миниатюры для {full_path}: {e}")
        return full_path

def clean_cache(valid_paths):
    if os.path.exists(CACHE_DIR):
        cached_thumbs = os.listdir(CACHE_DIR)
        valid_thumbs = [f"thumb_{p.replace('/', '_').strip('_')}" for p in valid_paths]
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
        self.last_swipe_time = 0  # Для предотвращения слишком быстрого пролистывания

    def do_activate(self):
        if self.win:
            self.win.present()
            return

        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_title("Выбор обоев")
        self.win.set_default_size(900, 600)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(main_box)

        # Заголовок
        header = Adw.HeaderBar()
        
        # Используем Adw.ViewStack
        self.view_stack = Adw.ViewStack()
        
        # --- НАСТРОЙКА НАДЁЖНОЙ АНИМАЦИИ ---
        self.view_stack.set_enable_transitions(True)
        self.view_stack.set_transition_duration(250)  # Длительность в мс
        # ------------------------------------
        
        # Используем родной Adw.ViewSwitcher
        view_switcher = Adw.ViewSwitcher(stack=self.view_stack)
        
        # Устанавливаем политику "narrow", чтобы сэкономить место
        view_switcher.set_policy(Adw.ViewSwitcherPolicy.NARROW) 
        
        header.set_title_widget(view_switcher)
        main_box.append(header)
        
        main_box.append(self.view_stack)

        # --- СКРЫВАЕМ ИКОНКИ ЧЕРЕЗ КОРРЕКТНЫЙ GTK CSS ---
        provider = Gtk.CssProvider()
        provider.load_from_data("""
            viewswitcher button image {
                opacity: 0;
                min-width: 0;
                min-height: 0;
                width: 0;
                height: 0;
                margin: 0;
                padding: 0;
                -gtk-icon-size: 0;
            }
            viewswitcher button label {
                margin-top: 0;
                margin-bottom: 0;
                padding-top: 6px;
                padding-bottom: 6px;
                font-size: 14px;
            }
        """.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        # ---------------------------------

        # --- ЖЕСТЫ ТАЧПАДА (2 пальца влево/вправо) ---
        scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.HORIZONTAL)
        scroll_controller.connect("scroll", self.on_trackpad_scroll)
        self.win.add_controller(scroll_controller)
        # ---------------------------------------------

        # Обработка клавиш (Esc)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.win.add_controller(key_controller)

        self.win.present()
        GLib.idle_add(self.load_wallpapers)

    def on_trackpad_scroll(self, controller, dx, dy):
        now = time.time()
        # Задержка 0.3 секунды между переключениями, чтобы вкладки не летели слишком быстро
        if now - self.last_swipe_time < 0.3:
            return True

        # Собираем список всех страниц в стэке
        pages = []
        pages_model = self.view_stack.get_pages()
        for i in range(pages_model.get_n_items()):
            page = pages_model.get_item(i)
            pages.append(page)

        if len(pages) <= 1:
            return False

        # Ищем текущую активную страницу
        current_visible = self.view_stack.get_visible_child()
        if not current_visible:
            return False

        current_index = -1
        for idx, page in enumerate(pages):
            if page.get_child() == current_visible:
                current_index = idx
                break

        if current_index == -1:
            return False

        # ИНВЕРТИРОВАННЫЙ ЖЕСТ:
        # dx > 0.5 (пальцы влево) -> следующая вкладка (вправо по списку)
        # dx < -0.5 (пальцы вправо) -> предыдущая вкладка (влево по списку)
        if dx > 0.5:
            next_index = (current_index + 1) % len(pages)
            self.view_stack.set_visible_child(pages[next_index].get_child())
            self.last_swipe_time = now
            return True
        elif dx < -0.5:
            next_index = (current_index - 1) % len(pages)
            self.view_stack.set_visible_child(pages[next_index].get_child())
            self.last_swipe_time = now
            return True

        return False

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.win.close()
            self.win = None
            return True
        return False

    def create_flowbox(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(6)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_margin_top(15)
        flowbox.set_margin_bottom(15)
        flowbox.set_margin_start(15)
        flowbox.set_margin_end(15)
        flowbox.set_column_spacing(15)
        flowbox.set_row_spacing(15)
        
        scrolled.set_child(flowbox)
        return scrolled, flowbox

    def load_wallpapers(self):
        if not os.path.exists(WALLPAPER_DIR):
            error_label = Gtk.Label(label=f"Папка не найдена: {WALLPAPER_DIR}")
            self.view_stack.add_titled(error_label, "error", "Ошибка")
            return False

        valid_exts = ('.jpg', '.jpeg', '.png', '.webp')
        
        categories = {
            "Все": []
        }
        all_filepaths = []

        # Сканируем директорию обоев
        for item in sorted(os.listdir(WALLPAPER_DIR)):
            item_path = os.path.join(WALLPAPER_DIR, item)
            
            if os.path.isfile(item_path) and item.lower().endswith(valid_exts):
                categories["Все"].append(item_path)
                all_filepaths.append(item_path)
                
            elif os.path.isdir(item_path):
                subfolder_name = item
                subfolder_files = []
                
                for sub_item in sorted(os.listdir(item_path)):
                    sub_item_path = os.path.join(item_path, sub_item)
                    if os.path.isfile(sub_item_path) and sub_item.lower().endswith(valid_exts):
                        subfolder_files.append(sub_item_path)
                        all_filepaths.append(sub_item_path)
                        categories["Все"].append(sub_item_path)
                
                if subfolder_files:
                    categories[subfolder_name] = subfolder_files

        clean_cache(all_filepaths)

        # Добавляем вкладки в интерфейс
        for category_name, files in categories.items():
            if not files:
                continue
                
            scrolled, flowbox = self.create_flowbox()
            
            # Добавляем вкладку в Adw.ViewStack.
            # Оставляем иконку пустой (""), чтобы не подтягивалась дефолтная папка.
            self.view_stack.add_titled_with_icon(
                scrolled, 
                category_name.lower().replace(" ", "_"), 
                category_name,
                ""
            )
            
            for full_path in files:
                filename = os.path.basename(full_path)
                thumb_path = get_thumbnail(full_path)
                
                btn = Gtk.Button()
                btn.add_css_class("flat")
                
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                
                img = Gtk.Image.new_from_file(thumb_path)
                img.set_pixel_size(160)
                img.set_size_request(160, 100)
                
                display_name = filename[:15] + '...' if len(filename) > 15 else filename
                lbl = Gtk.Label(label=display_name)
                lbl.add_css_class("caption")
                
                box.append(img)
                box.append(lbl)
                btn.set_child(box)
                
                btn.connect("clicked", self.on_click, full_path)
                flowbox.append(btn)
                
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
    sys.argv[0] = "wallpaper-picker"
    sys.exit(app.run(sys.argv))

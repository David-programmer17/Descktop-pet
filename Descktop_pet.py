import ctypes
import tkinter as tk
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Listener, Key
from PIL import Image, ImageTk
import random
import math
import json
import os

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except AttributeError:
    ctypes.windll.user32.SetProcessDPIAware()

class RealisticCubeGoose:
    def __init__(self, config_path="goose_config.json"):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Загружаем конфигурацию
        self.config = self.load_config(config_path)
        
        self.transparent_color = self.config.get("transparent_color", "#FF00FF")
        self.root.attributes("-transparentcolor", self.transparent_color)

        # ====== НАСТРОЙКИ СПРАЙТОВ ИЗ КОНФИГА ======
        self.body_image_path = self.config["sprites"]["body"]
        self.left_hand_image_path = self.config["sprites"]["left_hand"]
        self.right_hand_image_path = self.config["sprites"]["right_hand"]
        self.left_foot_image_path = self.config["sprites"]["left_foot"]
        self.right_foot_image_path = self.config["sprites"]["right_foot"]
        self.attack_body_image_path = self.config["sprites"]["body_attack"]
        self.steal_body_image_path = self.config["sprites"]["body_steal"]

        # ====== РАЗМЕРЫ ИЗ КОНФИГА ======
        sizes = self.config["sizes"]
        self.body_width = sizes["body_width"]
        self.body_height = sizes["body_height"]
        self.left_hand_width = sizes["left_hand_width"]
        self.left_hand_height = sizes["left_hand_height"]
        self.right_hand_width = sizes["right_hand_width"]
        self.right_hand_height = sizes["right_hand_height"]
        self.left_foot_width = sizes["left_foot_width"]
        self.left_foot_height = sizes["left_foot_height"]
        self.right_foot_width = sizes["right_foot_width"]
        self.right_foot_height = sizes["right_foot_height"]

        # ====== СКОРОСТИ ИЗ КОНФИГА ======
        speed = self.config["speed"]
        self.walk_speed_min = speed["walk_speed_min"]
        self.walk_speed_max = speed["walk_speed_max"]
        self.walk_acceleration = speed["walk_acceleration"]
        self.attack_speed = speed["attack_speed"]
        self.attack_acceleration = speed["attack_acceleration"]
        self.steal_speed = speed["steal_speed"]
        self.steal_acceleration = speed["steal_acceleration"]
        self.friction = speed["friction"]
        self.steal_friction = speed["steal_friction"]

        # ====== ОТСТУПЫ ИЗ КОНФИГА ======
        offsets = self.config["offsets"]
        self.left_hand_offset_x = offsets["left_hand_x"]
        self.left_hand_offset_y = offsets["left_hand_y"]
        self.right_hand_offset_x = offsets["right_hand_x"]
        self.right_hand_offset_y = offsets["right_hand_y"]
        self.left_foot_offset_x = offsets["left_foot_x"]
        self.left_foot_offset_y = offsets["left_foot_y"]
        self.right_foot_offset_x = offsets["right_foot_x"]
        self.right_foot_offset_y = offsets["right_foot_y"]

        # ====== АМПЛИТУДЫ ИЗ КОНФИГА ======
        amplitudes = self.config["amplitudes"]
        self.left_hand_swing_amplitude = amplitudes["left_hand_swing"]
        self.right_hand_swing_amplitude = amplitudes["right_hand_swing"]
        self.left_foot_swing_amplitude = amplitudes["left_foot_swing"]
        self.right_foot_swing_amplitude = amplitudes["right_foot_swing"]

        # ====== АНИМАЦИЯ ИЗ КОНФИГА ======
        animation = self.config["animation"]
        self.step_speed_modifier = animation["step_speed_modifier"]
        self.steal_anim_speed_factor = animation["steal_anim_speed_factor"]
        self.body_bounce_height = animation["body_bounce_height"]
        self.jump_height = animation["jump_height"]
        self.jump_recovery_speed = animation["jump_recovery_speed"]

        # ====== ПОВЕДЕНИЕ ИЗ КОНФИГА ======
        behavior = self.config["behavior"]
        self.idle_min_time = behavior["idle_min_time"]
        self.idle_max_time = behavior["idle_max_time"]
        self.steal_distance = behavior["steal_distance"]
        self.walk_stop_distance = behavior["walk_stop_distance"]
        self.attack_stop_distance = behavior["attack_stop_distance"]
        self.idle_state_duration = behavior["idle_state_duration"]
        self.mouse_steal_enabled = behavior.get("mouse_steal_enabled", True)

        # ====== ОКНО ======
        window = self.config.get("window", {})
        self.window_size = window.get("canvas_size", 300)
        self.start_x = window.get("start_x", 500)
        self.start_y = window.get("start_y", 500)
        
        self.canvas = tk.Canvas(self.root, width=self.window_size, height=self.window_size,
                                bg=self.transparent_color, highlightthickness=0)
        self.canvas.pack()

        self.mouse = MouseController()
        self.pil_images = {}
        self.tk_sprites = {}
        self.load_sprites()

        self.right_hand_img = self.canvas.create_image(0, 0, image=self.tk_sprites['right_hand'], anchor="nw")
        self.left_foot_img = self.canvas.create_image(0, 0, image=self.tk_sprites['left_foot'], anchor="nw")
        self.right_foot_img = self.canvas.create_image(0, 0, image=self.tk_sprites['right_foot'], anchor="nw")
        self.goose = self.canvas.create_image(0, 0, image=self.tk_sprites['body'], anchor="nw")
        self.left_hand_img = self.canvas.create_image(0, 0, image=self.tk_sprites['left_hand'], anchor="nw")

        self.canvas.tag_bind(self.goose, "<Button-1>", self.trigger_attack)

        self.x, self.y = self.start_x, self.start_y
        self.vx, self.vy = 0.0, 0.0
        self.facing_right = True
        self.state = "walk"
        self.target_x, self.target_y = self.x, self.y
        self.max_speed = self.walk_speed_min
        self.acceleration = self.walk_acceleration

        self.idle_timer = 0
        self.breathe_cycle = 0.0
        self.step_cycle = 0.0
        self.jump_offset = 0.0

        # ────────────── Глобальный слушатель клавиатуры ──────────────
        self.escape_timer_id = None
        self.keyboard_listener = Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.keyboard_listener.start()
        
        # ────────────── Горячая перезагрузка конфига ──────────────
        self.config_reload_key = self.config.get("reload_config_key", "f5")
        self.config_path = config_path

        self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
        self.update_behavior()
        self.root.mainloop()

    def load_config(self, config_path):
        """Загрузка конфигурации из JSON файла"""
        default_config = {
            "transparent_color": "#FF00FF",
            "sprites": {
                "body": "body.png",
                "left_hand": "Selecti111on.png",
                "right_hand": "Selecti111on.png",
                "left_foot": "Selecti111on.png",
                "right_foot": "Selecti111on.png",
                "body_attack": "body_attack.png",
                "body_steal": "body_steal.png"
            },
            "sizes": {
                "body_width": 80,
                "body_height": 90,
                "left_hand_width": 20,
                "left_hand_height": 22,
                "right_hand_width": 20,
                "right_hand_height": 22,
                "left_foot_width": 24,
                "left_foot_height": 18,
                "right_foot_width": 24,
                "right_foot_height": 18
            },
            "speed": {
                "walk_speed_min": 1.8,
                "walk_speed_max": 2.2,
                "walk_acceleration": 0.08,
                "attack_speed": 2.5,
                "attack_acceleration": 0.45,
                "steal_speed": 2.5,
                "steal_acceleration": 0.15,
                "friction": 0.92,
                "steal_friction": 0.85
            },
            "offsets": {
                "left_hand_x": 30,
                "left_hand_y": 50,
                "right_hand_x": 30,
                "right_hand_y": 50,
                "left_foot_x": 10,
                "left_foot_y": 6,
                "right_foot_x": 10,
                "right_foot_y": 6
            },
            "amplitudes": {
                "left_hand_swing": 1.3,
                "right_hand_swing": 1.3,
                "left_foot_swing": 1.0,
                "right_foot_swing": 1.0
            },
            "animation": {
                "step_speed_modifier": 0.15,
                "steal_anim_speed_factor": 0.6,
                "body_bounce_height": 2,
                "jump_height": -30,
                "jump_recovery_speed": 2.0
            },
            "behavior": {
                "idle_min_time": 60,
                "idle_max_time": 210,
                "steal_distance": 25,
                "walk_stop_distance": 20,
                "attack_stop_distance": 25,
                "idle_state_duration": 90,
                "mouse_steal_enabled": True
            },
            "window": {
                "canvas_size": 300,
                "start_x": 500,
                "start_y": 500
            },
            "reload_config_key": "f5"
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Объединяем с дефолтным конфигом для обратной совместимости
                config = self.merge_configs(default_config, loaded_config)
                print(f"Конфигурация загружена из {config_path}")
                return config
            else:
                # Создаем файл с конфигурацией по умолчанию
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                print(f"Создан файл конфигурации по умолчанию: {config_path}")
                return default_config
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            return default_config

    def merge_configs(self, default, loaded):
        """Рекурсивное объединение конфигов"""
        merged = default.copy()
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self.merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged

    def reload_config(self):
        """Горячая перезагрузка конфигурации"""
        try:
            new_config = self.load_config(self.config_path)
            self.config = new_config
            
            # Обновляем все параметры
            self.transparent_color = self.config.get("transparent_color", "#FF00FF")
            self.root.attributes("-transparentcolor", self.transparent_color)
            
            # Размеры
            sizes = self.config["sizes"]
            self.body_width = sizes["body_width"]
            self.body_height = sizes["body_height"]
            self.left_hand_width = sizes["left_hand_width"]
            self.left_hand_height = sizes["left_hand_height"]
            self.right_hand_width = sizes["right_hand_width"]
            self.right_hand_height = sizes["right_hand_height"]
            self.left_foot_width = sizes["left_foot_width"]
            self.left_foot_height = sizes["left_foot_height"]
            self.right_foot_width = sizes["right_foot_width"]
            self.right_foot_height = sizes["right_foot_height"]
            
            # Скорости
            speed = self.config["speed"]
            self.walk_speed_min = speed["walk_speed_min"]
            self.walk_speed_max = speed["walk_speed_max"]
            self.walk_acceleration = speed["walk_acceleration"]
            self.attack_speed = speed["attack_speed"]
            self.attack_acceleration = speed["attack_acceleration"]
            self.steal_speed = speed["steal_speed"]
            self.steal_acceleration = speed["steal_acceleration"]
            self.friction = speed["friction"]
            self.steal_friction = speed["steal_friction"]
            
            # Отступы
            offsets = self.config["offsets"]
            self.left_hand_offset_x = offsets["left_hand_x"]
            self.left_hand_offset_y = offsets["left_hand_y"]
            self.right_hand_offset_x = offsets["right_hand_x"]
            self.right_hand_offset_y = offsets["right_hand_y"]
            self.left_foot_offset_x = offsets["left_foot_x"]
            self.left_foot_offset_y = offsets["left_foot_y"]
            self.right_foot_offset_x = offsets["right_foot_x"]
            self.right_foot_offset_y = offsets["right_foot_y"]
            
            # Амплитуды
            amplitudes = self.config["amplitudes"]
            self.left_hand_swing_amplitude = amplitudes["left_hand_swing"]
            self.right_hand_swing_amplitude = amplitudes["right_hand_swing"]
            self.left_foot_swing_amplitude = amplitudes["left_foot_swing"]
            self.right_foot_swing_amplitude = amplitudes["right_foot_swing"]
            
            # Анимация
            animation = self.config["animation"]
            self.step_speed_modifier = animation["step_speed_modifier"]
            self.steal_anim_speed_factor = animation["steal_anim_speed_factor"]
            self.body_bounce_height = animation["body_bounce_height"]
            self.jump_height = animation["jump_height"]
            self.jump_recovery_speed = animation["jump_recovery_speed"]
            
            # Поведение
            behavior = self.config["behavior"]
            self.idle_min_time = behavior["idle_min_time"]
            self.idle_max_time = behavior["idle_max_time"]
            self.steal_distance = behavior["steal_distance"]
            self.walk_stop_distance = behavior["walk_stop_distance"]
            self.attack_stop_distance = behavior["attack_stop_distance"]
            self.idle_state_duration = behavior["idle_state_duration"]
            self.mouse_steal_enabled = behavior.get("mouse_steal_enabled", True)
            
            # Перезагружаем спрайты
            self.load_sprites()
            
            print("Конфигурация успешно перезагружена!")
        except Exception as e:
            print(f"Ошибка перезагрузки конфигурации: {e}")

    # ── Работа с изображениями ────────────────────────────
    def _open_image(self, path, width, height):
        try:
            img = Image.open(path).convert("RGBA")
            return img.resize((int(width), int(height)), Image.NEAREST)
        except Exception:
            return None

    def load_sprites(self):
        body_img = self._open_image(self.body_image_path, self.body_width, self.body_height)
        if body_img is None:
            body_img = Image.new("RGBA", (self.body_width, self.body_height), (0, 0, 0, 0))
        self.pil_images['body'] = body_img

        self.pil_images['left_hand'] = self._open_image(self.left_hand_image_path, self.left_hand_width, self.left_hand_height)
        if self.pil_images['left_hand'] is None:
            self.pil_images['left_hand'] = Image.new("RGBA", (self.left_hand_width, self.left_hand_height), (0, 0, 0, 0))
        self.pil_images['right_hand'] = self._open_image(self.right_hand_image_path, self.right_hand_width, self.right_hand_height)
        if self.pil_images['right_hand'] is None:
            self.pil_images['right_hand'] = Image.new("RGBA", (self.right_hand_width, self.right_hand_height), (0, 0, 0, 0))
        self.pil_images['left_foot'] = self._open_image(self.left_foot_image_path, self.left_foot_width, self.left_foot_height)
        if self.pil_images['left_foot'] is None:
            self.pil_images['left_foot'] = Image.new("RGBA", (self.left_foot_width, self.left_foot_height), (0, 0, 0, 0))
        self.pil_images['right_foot'] = self._open_image(self.right_foot_image_path, self.right_foot_width, self.right_foot_height)
        if self.pil_images['right_foot'] is None:
            self.pil_images['right_foot'] = Image.new("RGBA", (self.right_foot_width, self.right_foot_height), (0, 0, 0, 0))

        attack_img = self._open_image(self.attack_body_image_path, self.body_width, self.body_height)
        self.pil_images['body_attack'] = attack_img if attack_img is not None else body_img
        steal_img = self._open_image(self.steal_body_image_path, self.body_width, self.body_height)
        self.pil_images['body_steal'] = steal_img if steal_img is not None else body_img

        for key, img in self.pil_images.items():
            self.tk_sprites[key] = ImageTk.PhotoImage(img)

    # ── Вспомогательные методы ──────────────────────────
    def get_body_coords(self):
        center = self.window_size // 2
        half_width = self.body_width // 2
        half_height = self.body_height // 2
        bx1 = center - half_width
        by1 = center - half_height
        bx2 = center + half_width
        by2 = center + half_height
        return bx1, by1, bx2, by2

    def trigger_attack(self, event):
        if self.state in ["walk", "idle"]:
            self.state = "attack"
            self.max_speed = self.attack_speed
            self.acceleration = self.attack_acceleration
            self.canvas.itemconfig(self.goose, image=self.tk_sprites['body_attack'])
            self.jump_offset = self.jump_height

    # ── Глобальные события клавиатуры ───
    def on_key_press(self, key):
        if key == Key.esc:
            if self.escape_timer_id is None:
                self.escape_timer_id = self.root.after(2000, self.close_app)
        # Проверяем клавишу для перезагрузки конфига
        try:
            if hasattr(Key, self.config_reload_key) and key == getattr(Key, self.config_reload_key):
                self.reload_config()
        except:
            pass

    def on_key_release(self, key):
        if key == Key.esc:
            if self.escape_timer_id is not None:
                self.root.after_cancel(self.escape_timer_id)
                self.escape_timer_id = None

    def close_app(self):
        self.keyboard_listener.stop()
        self.root.destroy()

    # ── Основной цикл поведения ─────────────────────────
    def update_behavior(self):
        mouse_x, mouse_y = self.mouse.position
        center_x = self.x + self.window_size // 2
        center_y = self.y + self.window_size // 2
        dx_mouse = mouse_x - center_x
        dy_mouse = mouse_y - center_y
        distance_to_mouse = math.hypot(dx_mouse, dy_mouse)

        # ----- Логика состояний -----
        if self.state == "idle":
            self.canvas.itemconfig(self.goose, image=self.tk_sprites['body'])
            self.target_x, self.target_y = self.x, self.y
            self.idle_timer -= 1
            if self.idle_timer <= 0:
                self.state = "walk"
                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()
                self.target_x = random.randint(100, max(100, screen_w - self.window_size))
                self.target_y = random.randint(100, max(100, screen_h - self.window_size))
                self.max_speed = random.uniform(self.walk_speed_min, self.walk_speed_max)
                self.acceleration = self.walk_acceleration

        elif self.state == "walk":
            if math.hypot(self.target_x - self.x, self.target_y - self.y) < self.walk_stop_distance:
                self.state = "idle"
                self.idle_timer = random.randint(self.idle_min_time, self.idle_max_time)

        elif self.state == "attack":
            self.target_x = mouse_x - self.window_size // 2
            self.target_y = mouse_y - self.window_size // 2
            if distance_to_mouse < self.attack_stop_distance:
                self.state = "steal"
                self.canvas.itemconfig(self.goose, image=self.tk_sprites['body_steal'])
                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()
                if center_x < screen_w / 2:
                    self.target_x = screen_w - self.window_size
                else:
                    self.target_x = 0
                self.target_y = random.randint(100, max(100, screen_h - self.window_size))
                self.facing_right = (self.target_x > self.x)
                self.max_speed = self.steal_speed
                self.acceleration = self.steal_acceleration

        elif self.state == "steal":
            pass

        # ----- Физика движения -----
        target_dx = self.target_x - self.x
        target_dy = self.target_y - self.y
        target_dist = math.hypot(target_dx, target_dy)

        if target_dist > 1 and self.acceleration > 0:
            desired_vx = (target_dx / target_dist) * self.max_speed
            desired_vy = (target_dy / target_dist) * self.max_speed
            self.vx += (desired_vx - self.vx) * self.acceleration
            self.vy += (desired_vy - self.vy) * self.acceleration
        else:
            self.vx *= self.friction
            self.vy *= self.friction

        current_friction = self.steal_friction if self.state == "steal" else self.friction
        self.vx *= current_friction
        self.vy *= current_friction
        self.x += self.vx
        self.y += self.vy

        if self.state != "steal":
            if abs(self.vx) > 0.1:
                self.facing_right = self.vx > 0
            elif self.state == "attack":
                self.facing_right = mouse_x > center_x

        # ----- Анимация -----
        current_speed = math.hypot(self.vx, self.vy)

        if self.jump_offset < 0:
            self.jump_offset += self.jump_recovery_speed
        else:
            self.jump_offset = 0

        bx1, by1, bx2, by2 = self.get_body_coords()
        by1 += self.jump_offset
        by2 += self.jump_offset

        left_hand_global_x = None
        left_hand_global_y = None

        if self.state == "idle":
            self.breathe_cycle += 0.05
            self.canvas.coords(self.goose, bx1, by1)
            self.canvas.coords(self.left_hand_img,
                               bx1 - self.left_hand_offset_x, by1 + self.left_hand_offset_y)
            self.canvas.coords(self.right_hand_img,
                               bx2 + self.right_hand_offset_x - self.right_hand_width, by1 + self.right_hand_offset_y)
            self.canvas.coords(self.left_foot_img,
                               bx1 + self.left_foot_offset_x, by2 + self.left_foot_offset_y)
            self.canvas.coords(self.right_foot_img,
                               bx2 - self.right_foot_offset_x - self.right_foot_width, by2 + self.right_foot_offset_y)

        elif current_speed > 0.2 or self.state == "steal":
            if self.state == "steal":
                anim_speed = current_speed * self.steal_anim_speed_factor
            else:
                anim_speed = current_speed

            self.step_cycle += anim_speed * self.step_speed_modifier

            left_hand_swing = math.sin(self.step_cycle) * (self.body_width // 5) * self.left_hand_swing_amplitude
            right_hand_swing = math.sin(self.step_cycle) * (self.body_width // 5) * self.right_hand_swing_amplitude
            left_foot_swing = math.sin(self.step_cycle) * (self.body_width // 5) * self.left_foot_swing_amplitude
            right_foot_swing = math.sin(self.step_cycle) * (self.body_width // 5) * self.right_foot_swing_amplitude

            body_bounce = abs(math.sin(self.step_cycle)) * self.body_bounce_height

            if self.facing_right:
                lh_x = bx1 - self.left_hand_offset_x - left_hand_swing
                lh_y = by1 + self.left_hand_offset_y - body_bounce
                rh_x = bx2 + self.right_hand_offset_x - self.right_hand_width + right_hand_swing
                rh_y = by1 + self.right_hand_offset_y - body_bounce
                lf_x = bx1 + self.left_foot_offset_x + left_foot_swing
                lf_y = by2 + self.left_foot_offset_y
                rf_x = bx2 - self.right_foot_offset_x - self.right_foot_width - right_foot_swing
                rf_y = by2 + self.left_foot_offset_y
            else:
                lh_x = bx2 + self.right_hand_offset_x - self.right_hand_width + right_hand_swing
                lh_y = by1 + self.right_hand_offset_y - body_bounce
                rh_x = bx1 - self.left_hand_offset_x - left_hand_swing
                rh_y = by1 + self.left_hand_offset_y - body_bounce
                lf_x = bx2 - self.right_foot_offset_x - self.right_foot_width - right_foot_swing
                lf_y = by2 + self.right_foot_offset_y
                rf_x = bx1 + self.left_foot_offset_x + left_foot_swing
                rf_y = by2 + self.left_foot_offset_y

            self.canvas.coords(self.goose, bx1, by1 - body_bounce)
            self.canvas.coords(self.left_hand_img, lh_x, lh_y)
            self.canvas.coords(self.right_hand_img, rh_x, rh_y)
            self.canvas.coords(self.left_foot_img, lf_x, lf_y)
            self.canvas.coords(self.right_foot_img, rf_x, rf_y)
            
            left_hand_global_x = self.x + lh_x + self.left_hand_width // 2
            left_hand_global_y = self.y + lh_y + self.left_hand_height // 2
        else:
            self.canvas.coords(self.goose, bx1, by1)

        if self.state == "steal" and left_hand_global_x is not None and self.mouse_steal_enabled:
            try:
                self.mouse.position = (int(left_hand_global_x), int(left_hand_global_y))
            except Exception:
                pass
            if math.hypot(self.target_x - self.x, self.target_y - self.y) < self.steal_distance:
                self.state = "idle"
                self.idle_timer = self.idle_state_duration
                self.canvas.itemconfig(self.goose, image=self.tk_sprites['body'])

        self.root.geometry(f"+{int(self.x)}+{int(self.y)}")
        self.root.after(16, self.update_behavior)

if __name__ == "__main__":
    RealisticCubeGoose()
import math
import time
from random import randint, random
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.core.window import Window
import os
from kivy.graphics import Color, Mesh, Ellipse, Rectangle, PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
from game_objects import FallingItem
from kivy.animation import Animation
from kivy.uix.image import Image
from math import sqrt
import random as rnd
from audio_manager import AudioManager

Window.size = (800, 450)

Builder.load_file('mookata.kv')

class SlicedHalf(Image):
    def __init__(self, orig_texture, is_left, orig_center, orig_size, slash_angle, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (orig_size[0] / 2, orig_size[1])
        self.allow_stretch = True
        self.keep_ratio = False
        
        tw, th = orig_texture.width, orig_texture.height
        if is_left:
            self.texture = orig_texture.get_region(0, 0, tw / 2, th)
        else:
            self.texture = orig_texture.get_region(tw / 2, 0, tw / 2, th)
            
        alpha = slash_angle - 90
        rad = math.radians(alpha)
        w, h = orig_size
        dir_sign = -1 if is_left else 1
        
        local_x = dir_sign * w / 4
        start_cx = orig_center[0] + local_x * math.cos(rad)
        start_cy = orig_center[1] + local_x * math.sin(rad)
        self.pos = (start_cx - self.size[0] / 2, start_cy - self.size[1] / 2)
        
        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=alpha, origin=self.center)
        with self.canvas.after:
            PopMatrix()
            
        self.bind(pos=self.update_rot_origin)
        
        peak_local_x = local_x + (dir_sign * 30)
        peak_cx = orig_center[0] + peak_local_x * math.cos(rad)
        peak_cy = orig_center[1] + peak_local_x * math.sin(rad) + 50
        peak_pos = (peak_cx - self.size[0] / 2, peak_cy - self.size[1] / 2)
        
        target_local_x = local_x + (dir_sign * 100)
        target_cx = orig_center[0] + target_local_x * math.cos(rad)
        target_cy = orig_center[1] + target_local_x * math.sin(rad) - 400
        target_pos = (target_cx - self.size[0] / 2, target_cy - self.size[1] / 2)
        
        target_rot = alpha + (dir_sign * 120)
        
        anim_pos = Animation(pos=peak_pos, duration=0.3, t='out_quad') + \
                   Animation(pos=target_pos, opacity=0, duration=1.2, t='in_quad')
        anim_rot = Animation(angle=target_rot, duration=1.5, t='linear')
        
        anim_pos.bind(on_complete=self.remove_self)
        anim_pos.start(self)
        anim_rot.start(self.rot)

    def update_rot_origin(self, *args):
        self.rot.origin = self.center

    def remove_self(self, anim, widget):
        if self.parent:
            self.parent.remove_widget(self)

class MainMenuScreen(Screen):
    def on_enter(self):
        app = App.get_running_app()
        if hasattr(app, 'audio_manager'):
            app.audio_manager.play_bgm()

class SettingsScreen(Screen):

    def on_volume_change(self, current_volume):
        safe_volume = max(0, min(1, current_volume))
        print(f"Volume is now: {safe_volume}")
        app = App.get_running_app()
        if hasattr(app, 'audio_manager'):
            app.audio_manager.set_volume(safe_volume)
        
    def on_mute_change(self, is_muted):
        app = App.get_running_app()
        if hasattr(app, 'audio_manager'):
            app.audio_manager.set_mute(is_muted)
        if is_muted:
            print("Mute ON")
        else:
            print("Mute OFF")

class GameScreen(Screen):
    game_objects = []
    time_elapsed = 0
    score = 0
    combo_count = 0
    last_hit_time = 0
    is_paused = False
    time_scale = 1.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio = None
        # AudioManager is created lazily in on_enter to avoid
        # audio backend initialization/order issues.

    def on_enter(self):
        app = App.get_running_app()
        if hasattr(app, 'audio_manager'):
            self.audio = app.audio_manager
        self.game_objects = []
        self.time_elapsed = 0
        self.score = 0
        self.is_paused = False
        if 'current_score_label' in self.ids:
            self.ids.current_score_label.text = f"Score: {self.score}"
        self.combo_count = 0
        self.last_hit_time = 0
        self.temp_hp = 3
        self.last_bomb_time = -10.0
        self.last_special_time = -15.0
        self.bomb_protected = False
        self.special_on_cooldown = False
        self.is_frenzy = False
        self.time_scale = 1.0
        self.ids.combo_shadow.text = ""
        self.ids.combo_main.text = ""
        self.ids.combo_highlight.text = ""
        self.update_lives(self.temp_hp)
        # Ensure audio manager exists after app startup / event loop init
        if not hasattr(self, 'audio') or self.audio is None:
            try:
                self.audio = AudioManager()
            except Exception as e:
                print('Main: failed to create AudioManager on_enter:', e)
        
        if 'pause_overlay' in self.ids:
            self.ids.pause_overlay.opacity = 0
            self.ids.pause_overlay.disabled = True
            
        if hasattr(self, 'audio') and hasattr(self.audio, 'play_bgm'):
            self.audio.play_bgm()
        Clock.schedule_interval(self.game_loop, 1.0/60.0)
        self.spawn_next_item(0)
        self.time_scale = 1.0

    def on_leave(self):
        if hasattr(self, 'audio') and hasattr(self.audio, 'stop_bgm'):
            self.audio.stop_bgm()
        Clock.unschedule(self.game_loop)
        Clock.unschedule(self.spawn_next_item)
        Clock.unschedule(self.reset_special_cooldown)
        Clock.unschedule(self.stop_frenzy)
        Clock.unschedule(self.remove_bomb_protection)
        Clock.unschedule(self.spawn_frenzy_item)
        Clock.unschedule(self.reset_slowmo)

        for obj in self.game_objects:
            self.remove_widget(obj)
        self.game_objects.clear()

    def pause_game(self):
        self.is_paused = True
        if 'pause_overlay' in self.ids:
            overlay = self.ids.pause_overlay
            
            if overlay.parent:
                overlay.parent.remove_widget(overlay)
                self.add_widget(overlay)
                
            overlay.opacity = 1
            overlay.disabled = False

    def resume_game(self):
        self.is_paused = False
        if 'pause_overlay' in self.ids:
            self.ids.pause_overlay.opacity = 0
            self.ids.pause_overlay.disabled = True

    def quit_game(self):
        self.resume_game()
        game_over_screen = self.manager.get_screen('gameover')
        if hasattr(game_over_screen.ids, 'score_label'): 
            game_over_screen.ids.score_label.text = f"Your Score: {self.score}"
        game_over_screen.final_score = self.score 
        self.manager.current = "gameover"

    def spawn_next_item(self, dt):
        if self.is_paused:
            Clock.schedule_once(self.spawn_next_item, 0.1)
            return
            
        score = getattr(self, 'score', 0)
        raw_difficulty = 0.5 + (sqrt(score) / 8.0)
        difficulty_level = min(8.0, raw_difficulty)
    
        spawn_count = 1
        if difficulty_level > 1.5: spawn_count = randint(1, 2)
        if difficulty_level > 3.0: spawn_count = randint(2, 4)
        if difficulty_level > 5.0: spawn_count = randint(3, 5)
        
        active_bombs = sum(1 for item in self.game_objects if getattr(item, 'item_type', '') == 'bomb')
        time_since_last_bomb = self.time_elapsed - getattr(self, 'last_bomb_time', -10.0)
        time_since_last_special = self.time_elapsed - getattr(self, 'last_special_time', -10.0)
        
        bomb_spawned_this_wave = False
        has_special_item = any(getattr(item, 'item_type', '') in ['chili', 'ice'] for item in self.game_objects)
        special_spawned_this_wave = False

        for _ in range(spawn_count):
            item_type = 'normal'

            if difficulty_level > 0.5 and not getattr(self, 'bomb_protected', False):
                rand_val = random()

                base_bomb = 0.15
                chili_chance = min(0.05, 0.01 + (difficulty_level * 0.005))
                ice_chance = min(0.10, 0.02 + (difficulty_level * 0.01))

                can_spawn_special = (time_since_last_special > 10.0) and not has_special_item and not special_spawned_this_wave

                if rand_val < base_bomb: 
                    if active_bombs < 2 and (time_since_last_bomb > 2.0 or bomb_spawned_this_wave):
                        item_type = 'bomb'
                        bomb_spawned_this_wave = True
                        active_bombs += 1
                
                elif rand_val < (base_bomb + chili_chance):
                    if can_spawn_special:
                        item_type = 'chili'
                        special_spawned_this_wave = True
                
                elif rand_val < (base_bomb + chili_chance + ice_chance) and len(self.game_objects) >= 3:
                    if can_spawn_special:
                        item_type = 'ice'
                        special_spawned_this_wave = True
                    
            item = FallingItem(difficulty=difficulty_level, item_type=item_type)
            insert_idx = len(self.children) - 1 if len(self.children) > 0 else 0
            self.add_widget(item, index=insert_idx)
            self.game_objects.append(item)

        if bomb_spawned_this_wave:
            self.last_bomb_time = self.time_elapsed

        if special_spawned_this_wave:
            self.last_special_time = self.time_elapsed
            
        base_delay = max(0.8, 1.8 - (difficulty_level * 0.15))
        next_spawn_delay = base_delay + (randint(-2, 2) * 0.1)
        Clock.schedule_once(self.spawn_next_item, next_spawn_delay)

    def game_loop(self, dt):
        if self.is_paused: return
        self.time_elapsed += dt
        
        for item in self.game_objects[:]:
            item.update(self.time_scale) # 👇 ใส่ time_scale ตรงนี้
            if item.y < -item.height * 2:
                self.remove_widget(item)
                self.game_objects.remove(item)

    def check_collision(self, touch):
        current_time = time.time()
        
        trail = touch.ud.get('trail', [])
        if len(trail) >= 2:
            dx = trail[-1][0] - trail[0][0]
            dy = trail[-1][1] - trail[0][1]
        else:
            dx = touch.dx
            dy = touch.dy
            
        if dx == 0 and dy == 0:
            slash_angle = 90
        else:
            slash_angle = math.degrees(math.atan2(dy, dx))

        for item in self.game_objects[:]:
            if item.collide_point(touch.x, touch.y): 
                if item.is_bomb:
                    if hasattr(self, 'audio') and hasattr(self.audio, 'play_bomb'):
                        self.audio.play_bomb()
                    self.test_damage() 
                    self.combo_count = 0
                    self.ids.combo_shadow.text = ""
                    self.ids.combo_main.text = ""
                    self.ids.combo_highlight.text = ""
                    self.create_bomb_effect(touch.x, touch.y)
                    self.trigger_screenshake()
                    self.remove_widget(item)
                    self.game_objects.remove(item)
                elif item.item_type == 'ice':
                    # ฟันโดนน้ำแข็ง
                    if hasattr(self, 'audio') and hasattr(self.audio, 'play_slash'):
                        self.audio.play_slash()
                    self.trigger_slowmo()
                    self.create_slice_effect(item, slash_angle)
                    self.remove_widget(item)
                    self.game_objects.remove(item)
                elif item.item_type == 'chili':
                    # ฟันโดนพริก
                    if hasattr(self, 'audio') and hasattr(self.audio, 'play_slash'):
                        self.audio.play_slash()
                    self.trigger_frenzy()
                    self.create_slice_effect(item, slash_angle)
                    self.remove_widget(item)
                    self.game_objects.remove(item)
                else:
                    if hasattr(self, 'audio') and hasattr(self.audio, 'play_slash'):
                        self.audio.play_slash()
                    
                    is_in_frenzy = getattr(item, 'is_frenzy_bonus', False) or getattr(self, 'is_frenzy', False)
                    
                    if is_in_frenzy:
                        self.score += 10
                    else:
                        if current_time - self.last_hit_time < 1.0: self.combo_count += 1
                        else: self.combo_count = 1
                        self.last_hit_time = current_time
                        self.score += 10 * self.combo_count

                    self.ids.current_score_label.text = f"Score: {self.score}"

                    if self.combo_count > 1 and not is_in_frenzy: 
                        self.show_combo_text(touch.x, touch.y)
                        
                    self.create_slice_effect(item, slash_angle)
                    self.create_hit_effect(touch.x, touch.y)
                    self.remove_widget(item)
                    self.game_objects.remove(item)

    def trigger_screenshake(self):
        magnitude = 10
        duration = 0.04

        anim = Animation(x=rnd.uniform(-magnitude, magnitude), y=rnd.uniform(-magnitude, magnitude), duration=duration, t='linear') #
        anim += Animation(x=rnd.uniform(-magnitude, magnitude), y=rnd.uniform(-magnitude, magnitude), duration=duration, t='linear') #
        anim += Animation(x=rnd.uniform(-magnitude, magnitude), y=rnd.uniform(-magnitude, magnitude), duration=duration, t='linear') #
        anim += Animation(x=0, y=0, duration=duration, t='out_quad') #

        anim.start(self)


    def create_slice_effect(self, item, slash_angle):
        if not item.texture: return
        orig_center = item.center
        half_1 = SlicedHalf(item.texture, True, orig_center, item.size, slash_angle)
        half_2 = SlicedHalf(item.texture, False, orig_center, item.size, slash_angle)
        
        insert_idx = len(self.children) - 1 if len(self.children) > 0 else 0
        self.add_widget(half_1, index=insert_idx)
        self.add_widget(half_2, index=insert_idx)

    def create_bomb_effect(self, x, y):
        with self.canvas.after:
            flash_color = Color(1, 0, 0, 0.6)
            flash_rect = Rectangle(pos=(0, 0), size=Window.size)
            wave1_color = Color(1, 0.4, 0, 0.9)
            wave1 = Ellipse(pos=(x-50, y-50), size=(100, 100))
            wave2_color = Color(1, 0.8, 0, 0.9)
            wave2 = Ellipse(pos=(x-25, y-25), size=(50, 50))

        anim_flash = Animation(a=0, duration=0.3)
        anim_w1 = Animation(size=(400, 400), pos=(x-200, y-200), duration=0.5, t='out_quad')
        anim_c1 = Animation(a=0, duration=0.5)
        anim_w2 = Animation(size=(250, 250), pos=(x-125, y-125), duration=0.4, t='out_quad')
        anim_c2 = Animation(a=0, duration=0.4)

        def remove_effect(anim, widget):
            self.canvas.after.remove(flash_color)
            self.canvas.after.remove(flash_rect)
            self.canvas.after.remove(wave1_color)
            self.canvas.after.remove(wave1)
            self.canvas.after.remove(wave2_color)
            self.canvas.after.remove(wave2)

        anim_w1.bind(on_complete=remove_effect)
        anim_flash.start(flash_color)
        anim_w1.start(wave1)
        anim_c1.start(wave1_color)
        anim_w2.start(wave2)
        anim_c2.start(wave2_color)

    def create_hit_effect(self, x, y):
        with self.canvas.after:
            color = Color(1, 1, 0.8, 1)
            ellipse = Ellipse(pos=(x-20, y-20), size=(40, 40))
        
        anim_size = Animation(size=(100, 100), pos=(x-50, y-50), duration=0.2)
        anim_alpha = Animation(a=0, duration=0.2)
        
        def remove_effect(anim, widget):
            self.canvas.after.remove(color)
            self.canvas.after.remove(ellipse)
            
        anim_size.bind(on_complete=remove_effect)
        anim_size.start(ellipse)
        anim_alpha.start(color)

    def show_combo_text(self, item_x, item_y):
        txt = f"{self.combo_count}x\nCOMBO!"
        margin = 100
        safe_x = max(margin, min(item_x, Window.width - margin))
        safe_y = max(margin, min(item_y + 80, Window.height - margin))
        normal_size = 60
        pop_size = 90
        
        main_color = (1, 0.85, 0, 1)
        shadow_color = (0.6, 0.45, 0, 1)
        highlight_color = (1, 1, 0.4, 1)

        for lbl_id in ['combo_shadow', 'combo_main', 'combo_highlight']:
            lbl = self.ids[lbl_id]
            lbl.text = txt
            lbl.font_size = normal_size
            lbl.center_x = safe_x
            lbl.center_y = safe_y
            if lbl_id == 'combo_shadow':
                lbl.color = shadow_color
                lbl.center_y -= 3
            elif lbl_id == 'combo_highlight':
                lbl.color = highlight_color
                lbl.center_y += 3
            else:
                lbl.color = main_color
        anim = Animation(font_size=pop_size, duration=0.1, t='out_back') + \
               Animation(font_size=normal_size, duration=0.1)
        anim.start(self.ids.combo_shadow)
        anim.start(self.ids.combo_main)
        anim.start(self.ids.combo_highlight)
        Clock.unschedule(self.hide_combo_text)
        Clock.schedule_once(self.hide_combo_text, 1.5)

    def hide_combo_text(self, dt):
        for lbl_id in ['combo_shadow', 'combo_main', 'combo_highlight']:
            lbl = self.ids[lbl_id]
            lbl.text = ""
            lbl.color = (0, 0, 0, 0)


    def on_touch_down(self, touch):
        if self.is_paused:
            return super().on_touch_down(touch)
            
        if hasattr(self, 'audio') and hasattr(self.audio, 'play_slash'):
            self.audio.play_slash()
        touch.ud['trail'] = [(touch.x, touch.y)]
        self.check_collision(touch)
        with self.canvas:
            touch.ud['color_glow'] = Color(1, 0.4, 0, 0.4)
            touch.ud['mesh_glow'] = Mesh(mode='triangle_strip')
            touch.ud['color_core'] = Color(1, 0.9, 0.2, 1)
            touch.ud['mesh_core'] = Mesh(mode='triangle_strip')
        touch.ud['decay_event'] = Clock.schedule_interval(lambda dt: self.decay_trail(touch), 0.02)
        return super().on_touch_down(touch)

    def decay_trail(self, touch):
        if 'trail' not in touch.ud or len(touch.ud['trail']) <= 2: return
        touch.ud['trail'].pop(0)
        self.update_slash(touch)

    def on_touch_move(self, touch):
        if self.is_paused:
            return super().on_touch_move(touch)
            
        self.check_collision(touch)
        if 'trail' not in touch.ud: return super().on_touch_move(touch)
        last_x, last_y = touch.ud['trail'][-1]
        if math.hypot(touch.x - last_x, touch.y - last_y) > 10:
            touch.ud['trail'].append((touch.x, touch.y))
            if len(touch.ud['trail']) > 12: touch.ud['trail'].pop(0)
            self.update_slash(touch)
        return super().on_touch_move(touch)

    def update_slash(self, touch):
        trail = touch.ud['trail']
        if len(trail) < 2: return
        v_glow, v_core, indices = [], [], []
        for i in range(len(trail)):
            x, y = trail[i]
            progress = i / (len(trail) - 1)
            curve = math.sin((progress ** 2) * math.pi)
            thick_glow, thick_core = curve * 25, curve * 8
            if i < len(trail) - 1: dx, dy = trail[i+1][0] - x, trail[i+1][1] - y
            else: dx, dy = x - trail[i-1][0], y - trail[i-1][1]
            length = math.hypot(dx, dy)
            px, py = (-dy/length, dx/length) if length else (0,0)
            v_glow.extend([x+px*thick_glow, y+py*thick_glow, 0, 0, x-px*thick_glow, y-py*thick_glow, 0, 0])
            v_core.extend([x+px*thick_core, y+py*thick_core, 0, 0, x-px*thick_core, y-py*thick_core, 0, 0])
            indices.extend([i*2, i*2+1])
        touch.ud['mesh_glow'].vertices = v_glow
        touch.ud['mesh_glow'].indices = indices
        touch.ud['mesh_core'].vertices = v_core
        touch.ud['mesh_core'].indices = indices

    def on_touch_up(self, touch):
        if self.is_paused:
            return super().on_touch_up(touch)
            
        if 'decay_event' in touch.ud: touch.ud['decay_event'].cancel()
        if 'mesh_glow' in touch.ud:
            self.canvas.remove(touch.ud['color_glow'])
            self.canvas.remove(touch.ud['mesh_glow'])
            self.canvas.remove(touch.ud['color_core'])
            self.canvas.remove(touch.ud['mesh_core'])
        return super().on_touch_up(touch)

    def update_lives(self, current_lives):
        for i in range(1, 4):
            getattr(self.ids, f'life_{i}').source = f'assets/images/heart_{"full" if current_lives >= i else "empty"}.png'

    def test_damage(self):
        if not hasattr(self, 'temp_hp'): self.temp_hp = 3
        self.temp_hp -= 1
        self.update_lives(self.temp_hp)
        if self.temp_hp <= 0:
            game_over_screen = self.manager.get_screen('gameover')
            if hasattr(game_over_screen.ids, 'score_label'): 
                game_over_screen.ids.score_label.text = f"Your Score: {self.score}"
            game_over_screen.final_score = self.score 
            self.manager.current = "gameover"

    def trigger_slowmo(self):
        self.time_scale = 0.3  # ทำให้เกมช้าลงเหลือ 30%
        Clock.unschedule(self.reset_slowmo)
        Clock.schedule_once(self.reset_slowmo, 3.0) # สโลว์นาน 3 วินาที

    def reset_slowmo(self, dt):
        self.time_scale = 1.0  # คืนค่าเวลาให้ปกติ

    def trigger_frenzy(self):
        self.is_frenzy = True 
        self.bomb_protected = True
        
        Clock.unschedule(self.stop_frenzy)
        Clock.schedule_interval(self.spawn_frenzy_item, 0.15) 
        Clock.schedule_once(self.stop_frenzy, 2.0) 

    def stop_frenzy(self, dt):
        self.is_frenzy = False
        Clock.unschedule(self.spawn_frenzy_item)
        
        Clock.schedule_once(self.remove_bomb_protection, 2.0)

    def remove_bomb_protection(self, dt):
        self.bomb_protected = False

    def reset_special_cooldown(self, dt):
        self.special_on_cooldown = False

    def spawn_frenzy_item(self, dt):
        if self.is_paused: return
        item = FallingItem(difficulty=3.0, item_type='normal')
        
        item.is_frenzy_bonus = True

        item.y = -50
        item.x = randint(100, Window.width - 100)
        
        insert_idx = len(self.children) - 1 if len(self.children) > 0 else 0
        self.add_widget(item, index=insert_idx)
        self.game_objects.append(item)

class GameOverScreen(Screen):
    final_score = 0 
    def on_enter(self): self.load_highscore()
    def load_highscore(self):
        if os.path.exists("highscore.txt"):
            with open("highscore.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
            parsed_scores = []
            for line in lines:
                try:
                    name_part, score_part = line.split(": ")
                    parsed_scores.append({"name": name_part, "score": int(score_part)})
                except (ValueError, IndexError):
                    pass
            if not parsed_scores:
                self.ids.highscore_label.text = "No Scores Yet"
                return
            top_entry = max(parsed_scores, key=lambda x: x['score'])
            
            recent_entries = parsed_scores[-3:][::-1] 
            
            display_text = f"TOP SCORE: {top_entry['name']}: {top_entry['score']}\n\nRECORDS 3 RECENT:\n"
            for entry in recent_entries:
                display_text += f"{entry['name']}: {entry['score']}\n"
            
            self.ids.highscore_label.text = display_text
    def save_score(self):
        name = self.ids.player_name.text if self.ids.player_name.text.strip() else "Unknown Ninja"
        with open("highscore.txt", "a", encoding="utf-8") as f: f.write(f"{name}: {self.final_score}\n")
        self.ids.player_name.text = "" 
        self.load_highscore()
    def restart_game(self): self.manager.current = "game"

class WindowManager(ScreenManager): pass
class MookataNinjaApp(App):
    def build(self): 
        self.audio_manager = AudioManager()
        return WindowManager()

if __name__ == '__main__': MookataNinjaApp().run()
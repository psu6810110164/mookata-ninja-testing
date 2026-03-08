from math import sqrt
from random import randint, choice
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, PushMatrix, PopMatrix, Rotate, Scale
from kivy.animation import Animation
from kivy.clock import Clock

class FallingItem(Image):
    def __init__(self, difficulty=1.0, item_type='normal', **kwargs):
        super().__init__(**kwargs)
        
        self.item_type = item_type
        self.is_bomb = (self.item_type == 'bomb')
        
        if self.item_type == 'bomb':
            self.source = 'assets/images/bombb.png'
        elif self.item_type == 'ice':
            self.source = 'assets/images/ice.png'
        elif self.item_type == 'chili':
            self.source = 'assets/images/chili.png'
        else:
            self.source = choice(['assets/images/ood.png', 'assets/images/vegtb.png', 'assets/images/meat.png', 'assets/images/tomato.png'])
            
        self.size_hint = (None, None)
        base_size = Window.height * 0.15
        
        if self.is_bomb:
            self.size = (base_size * 2, base_size * 2)
        else:
            self.size = (base_size, base_size)
            
        screen_w = Window.width
        self.x = randint(int(screen_w * 0.1), int(screen_w * 0.9))
        self.y = -self.height

        if self.is_bomb:
            target_height = Window.height * (randint(60, 75) / 100.0)
        else:
            target_height = Window.height * (randint(60, 85) / 100.0)
            
        distance_to_travel = target_height - self.y

        speed_multiplier = 1.0 + (difficulty * 0.05)
        
        if self.is_bomb:
            speed_multiplier *= 0.7
        
        self.gravity = (Window.height * 0.0005) * speed_multiplier
        self.velocity_y = sqrt(2 * self.gravity * distance_to_travel)
        
        x_force = Window.width * 0.005 * speed_multiplier
        if self.x < screen_w / 2:
            self.velocity_x = randint(int(x_force * 0.5), int(x_force))
        else:
            self.velocity_x = randint(int(-x_force), int(-x_force * 0.5))
            
        self.angle = 0
        
        if self.item_type == 'chili':
            self.rotation_speed = randint(6, 12) * speed_multiplier * choice([-1, 1])
        else:
            self.rotation_speed = randint(-3, 3) * speed_multiplier
        
        with self.canvas.before:
            if self.item_type == 'chili':
                Color(1, 0.5, 0, 0.5)  # สีส้มของพริก
                glow_size = (self.width * 1.3, self.height * 1.3)
                self.glow = Ellipse(size=glow_size)
            elif self.item_type == 'ice':
                self.glow_color = Color(0.2, 0.8, 1.0, 0.6)  # สีฟ้าของน้ำแข็ง
                glow_size = (self.width * 1.3, self.height * 1.3)
                self.glow = Ellipse(size=glow_size)
            
            PushMatrix()
            self.rot = Rotate()
            self.rot.origin = self.center
            self.rot.angle = self.angle
            self.scale = Scale(1, 1, 1)
            self.scale.origin = self.center
        with self.canvas.after:
            PopMatrix()
            
        self.bind(pos=self.update_canvas, size=self.update_canvas)

        # 👇 เรียกใช้เอฟเฟกต์ตามชนิดไอเทม
        if self.item_type == 'chili':
            Clock.schedule_once(self.start_chili_effects, 0.1)
        elif self.item_type == 'ice':
            Clock.schedule_once(self.start_ice_effects, 0.1)

    def start_chili_effects(self, dt):
        pulse_anim = Animation(x=1.3, y=1.3, duration=0.15, t='out_quad') + \
                     Animation(x=1.0, y=1.0, duration=0.15, t='in_quad')
        pulse_anim.repeat = True
        pulse_anim.start(self.scale)

    def start_ice_effects(self, dt):
        # ให้น้ำแข็งมีแสงวิบวับสลับไปมา (ปรับความทึบแสง)
        blink_anim = Animation(a=0.2, duration=0.5, t='in_out_quad') + \
                     Animation(a=0.7, duration=0.5, t='in_out_quad')
        blink_anim.repeat = True
        blink_anim.start(self.glow_color)

    def update_canvas(self, *args):
        if hasattr(self, 'glow'):
            self.glow.pos = (self.center_x - self.glow.size[0]/2, self.center_y - self.glow.size[1]/2)
            
        self.rot.origin = self.center
        self.rot.angle = self.angle
        self.scale.origin = self.center

    def update(self, time_scale=1.0):
        self.x += self.velocity_x * time_scale
        self.y += self.velocity_y * time_scale
        self.velocity_y -= self.gravity * time_scale
        self.angle += self.rotation_speed * time_scale
        self.update_canvas()
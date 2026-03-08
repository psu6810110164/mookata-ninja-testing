from kivy.clock import Clock
from kivy.core.window import Window

class GameEngine:
    def __init__(self):
        self.score = 0
        self.lives = 3
        self.spawn_rate = 2.0

    def start_game(self):
        self.score = 0
        self.lives = 3
        Clock.schedule_interval(self.spawn_item, self.spawn_rate)
        Clock.schedule_interval(self.update, 1.0 / 60.0)

    def stop_game(self):
        Clock.unschedule(self.spawn_item)
        Clock.unschedule(self.update)

    def spawn_item(self, dt):
        pass

    def update(self, dt):
        pass

    def check_collision(self, touch_pos):
        pass

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.game_over()

    def game_over(self):
        self.stop_game()
from kivy.core.audio import SoundLoader
import os

class AudioManager:
    def __init__(self):
        # store paths so we can attempt lazy reloads/fallbacks later
        self.slash_path = 'assets/sounds/slash.mp3'
        self.bomb_path = 'assets/sounds/bomb.mp3'
        self.bgm_path = 'assets/sounds/bgm.mp3'

        self.slash_sound = None
        self.sizzle_sound = None
        self.bg_music = None

        # เพิ่มตัวแปรสำหรับจำค่าระดับเสียงปัจจุบัน และสถานะ Mute
        self.current_volume = 0.5 
        self.is_muted = False

        # initial load (may return None if no provider/decoder available)
        self._load_all()
        
        # ตั้งค่าระดับเสียงเริ่มต้นให้ทุกไฟล์ตอนเปิดเกม
        self._apply_volume(self.current_volume)

    def _safe_load(self, path):
        try:
            s = SoundLoader.load(path)
            print(f"AudioManager: try load '{path}' -> {s}")
            return s
        except Exception as e:
            print(f"AudioManager: exception loading '{path}': {e}")
            return None

    def _load_all(self):
        self.slash_sound = self._safe_load(self.slash_path)
        self.sizzle_sound = self._safe_load(self.bomb_path)
        self.bg_music = self._safe_load(self.bgm_path)
        print("AudioManager: bgm object:", self.bg_music)

    def _try_fallback(self, path):
        # try same filename with .wav extension if exists
        root, _ = os.path.splitext(path)
        wav = root + '.wav'
        if os.path.exists(wav):
            return self._safe_load(wav)
        return None

    def play_slash(self):
        if not self.slash_sound:
            self.slash_sound = self._safe_load(self.slash_path) or self._try_fallback(self.slash_path)
        
        # เช็กสถานะ Mute และให้ใช้ค่า current_volume
        if self.slash_sound and not self.is_muted:
            try:
                self.slash_sound.volume = self.current_volume
                self.slash_sound.play()
                print('AudioManager: play_slash -> played')
            except Exception as e:
                print('AudioManager: play_slash -> error playing:', e)
        elif not self.slash_sound:
            print('AudioManager: play_slash -> no sound loaded')

    def play_bgm(self):
        if not self.bg_music:
            self.bg_music = self._safe_load(self.bgm_path) or self._try_fallback(self.bgm_path)
        
        if self.bg_music:
            try:
                self.bg_music.loop = True
                try:
                    self.bg_music.volume = 0 if self.is_muted else self.current_volume
                except Exception:
                    pass
                
                # เช็คว่าเพลงเล่นอยู่แล้วหรือเปล่า ถ้ายังไม่เล่นถึงจะสั่ง play
                if self.bg_music.state != 'play':
                    self.bg_music.play()
                print('AudioManager: play_bgm -> playing')
            except Exception as e:
                print('AudioManager: play_bgm -> error playing:', e)
        else:
            print('AudioManager: play_bgm -> no bgm loaded')

    def play_bomb(self):
        if not self.sizzle_sound:
            self.sizzle_sound = self._safe_load(self.bomb_path) or self._try_fallback(self.bomb_path)
        
        if self.sizzle_sound and not self.is_muted:
            try:
                # เร่งเสียงระเบิดให้ดังขึ้น 1.5 เท่า (แต่กำหนดค่าสูงสุดไม่เกิน 1.0)
                self.sizzle_sound.volume = min(1.0, self.current_volume * 1.5)
                self.sizzle_sound.play()
                print('AudioManager: play_bomb -> played')
            except Exception as e:
                print('AudioManager: play_bomb -> error playing:', e)
        elif not self.sizzle_sound:
            print('AudioManager: play_bomb -> no sound loaded')

    # ... (ข้ามฟังก์ชัน stop_bgm, set_volume, set_mute ปล่อยไว้เหมือนเดิม) ...

    def _apply_volume(self, volume):
        if self.slash_sound:
            self.slash_sound.volume = volume
        if self.sizzle_sound:
            # เวลาผู้เล่นปรับเสียงหลัก เสียงระเบิดก็ต้องคงความดัง 1.5 เท่าไว้ด้วย
            self.sizzle_sound.volume = min(1.0, volume * 1.5)
        if self.bg_music:
            try:
                self.bg_music.volume = volume
            except Exception:
                pass



    def stop_bgm(self):
        if self.bg_music:
            try:
                self.bg_music.stop()
                print('AudioManager: stop_bgm -> stopped')
            except Exception as e:
                print('AudioManager: stop_bgm -> error stopping:', e)
        else:
            print('AudioManager: stop_bgm -> no bgm loaded')

    # ---- ฟังก์ชันสำหรับ Settings ----

    def set_volume(self, volume):
        self.current_volume = volume
        if not self.is_muted:
            self._apply_volume(volume)

    def set_mute(self, is_muted):
        self.is_muted = is_muted
        if self.is_muted:
            self._apply_volume(0)  
        else:
            self._apply_volume(self.current_volume)  
import unittest
from unittest.mock import patch, MagicMock
from src.audio_manager import AudioManager

class TestAudioManagerWithStub(unittest.TestCase):

    @patch('src.audio_manager.SoundLoader.load')
    def test_play_bgm_with_stub(self, mock_sound_loader):
        stub_sound = MagicMock() 
        stub_sound.state = 'stop' 
        mock_sound_loader.return_value = stub_sound 

        audio_manager = AudioManager()
        audio_manager.play_bgm() 

        stub_sound.play.assert_called_once()
        
    @patch('src.audio_manager.SoundLoader.load')
    def test_mute_stops_volume(self, mock_sound_loader):
        stub_sound = MagicMock()
        mock_sound_loader.return_value = stub_sound
        audio_manager = AudioManager()
        
        audio_manager.set_mute(True)
        
        self.assertEqual(stub_sound.volume, 0)
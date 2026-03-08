import unittest
from unittest.mock import patch
from src.game_logic import GameEngine 

class TestGameEngine(unittest.TestCase):

    def setUp(self):
        self.engine = GameEngine()

    def test_initial_state(self):
        self.assertEqual(self.engine.lives, 3)
        self.assertEqual(self.engine.score, 0)

    @patch('src.game_logic.Clock') 
    def test_lose_life_decreases_lives(self, mock_clock):
        self.engine.start_game()
        self.engine.lose_life()
        self.assertEqual(self.engine.lives, 2) 

    @patch('src.game_logic.Clock')
    def test_game_over_when_lives_reach_zero(self, mock_clock):
        self.engine.start_game()
        self.engine.lives = 1
        with patch.object(self.engine, 'game_over') as mock_game_over:
            self.engine.lose_life()
            self.assertEqual(self.engine.lives, 0)
            mock_game_over.assert_called_once()
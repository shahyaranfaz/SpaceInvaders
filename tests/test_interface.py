import unittest

import pygame

from interface import ScrollArea


class ScrollAreaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_scrolling_is_clamped_to_content_bounds(self):
        area = ScrollArea(0, 0, 200, 100, 160)

        for _ in range(10):
            area.scroll_down()
        self.assertEqual(60, area.scroll_y)

        for _ in range(10):
            area.scroll_up()
        self.assertEqual(0, area.scroll_y)

    def test_content_that_fits_does_not_scroll(self):
        area = ScrollArea(0, 0, 200, 100, 100)

        area.scroll_down()

        self.assertEqual(0, area.scroll_y)
        self.assertEqual(pygame.Rect(0, 0, 0, 0), area._scrollbar_rect())


if __name__ == "__main__":
    unittest.main()

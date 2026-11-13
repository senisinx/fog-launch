import unittest

from fog_launch import arrange
from fog_launch.arrange import MIN_SIZE, Monitor, View

# The user's ultrawide on the left, a 1080p monitor on its right, each with a 48 px taskbar.
WIDE = Monitor((0, 0, 3440, 1440), (0, 0, 3440, 1392), True)
SIDE = Monitor((3440, 0, 1920, 1080), (3440, 0, 1920, 1032))


class LayoutTests(unittest.TestCase):
    def test_grid_fills_the_work_area_without_overlap(self):
        rects = arrange.grid(4, WIDE.work)
        self.assertEqual(rects, [(0, 0, 1720, 696), (1720, 0, 1720, 696), (0, 696, 1720, 696), (1720, 696, 1720, 696)])
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                self.assertFalse(arrange.overlaps(a, b))

    def test_a_short_last_row_is_centred(self):
        rects = arrange.grid(3, (0, 0, 1000, 1000))
        self.assertEqual(rects[2], (250, 500, 500, 500))

    def test_row_and_column(self):
        self.assertEqual(arrange.side_by_side(2, WIDE.work), [(0, 0, 1720, 1392), (1720, 0, 1720, 1392)])
        self.assertEqual(arrange.stacked(2, WIDE.work), [(0, 0, 3440, 696), (0, 696, 3440, 696)])
        self.assertEqual(arrange.grid(0, WIDE.work), [])

    def test_one_per_monitor_and_spreading(self):
        self.assertEqual(arrange.one_per_monitor(2, [SIDE, WIDE]), [WIDE.work, SIDE.work])
        three = arrange.layout("row", 3, [WIDE, SIDE])
        self.assertEqual(three[:2], [(0, 0, 1720, 1392), (1720, 0, 1720, 1392)])
        self.assertEqual(three[2], SIDE.work)
        self.assertEqual(arrange.layout("column", 2, [WIDE]), arrange.stacked(2, WIDE.work))

    def test_keep_ratio_centres_a_16_9_window(self):
        (x, y, w, h), = arrange.keep_ratio([(0, 0, 1720, 1392)])
        self.assertEqual((w, h), (1720, 968))
        self.assertEqual((x, y), (0, 212))
        (x, y, w, h), = arrange.keep_ratio([WIDE.work])
        self.assertAlmostEqual(w / h, 16 / 9, places=2)
        self.assertEqual(x, (3440 - w) // 2)


class DragTests(unittest.TestCase):
    def test_moving_snaps_to_the_monitor_edge_and_to_a_neighbour(self):
        self.assertEqual(arrange.snap_move((9, 5, 800, 600), [WIDE], []), (0, 0, 800, 600))
        self.assertEqual(arrange.snap_move((1000, 300, 800, 600), [WIDE], []), (1000, 300, 800, 600))
        neighbour = (0, 0, 1000, 700)
        self.assertEqual(arrange.snap_move((1010, 0, 800, 600), [WIDE], [neighbour]), (1000, 0, 800, 600))
        # the right edge snaps to the work area's right edge
        self.assertEqual(arrange.snap_move((2632, 300, 800, 600), [WIDE], []), (2640, 300, 800, 600))

    def test_resizing_moves_one_corner_and_never_below_the_minimum(self):
        self.assertEqual(arrange.resize((100, 100, 800, 600), "se", 50, -20), (100, 100, 850, 580))
        self.assertEqual(arrange.resize((100, 100, 800, 600), "nw", 50, 40), (150, 140, 750, 560))
        tiny = arrange.resize((100, 100, 800, 600), "se", -900, -900)
        self.assertEqual(tiny[2:], (MIN_SIZE, MIN_SIZE))
        tiny = arrange.resize((100, 100, 800, 600), "nw", 900, 900)
        self.assertEqual(tiny, (700, 500, MIN_SIZE, MIN_SIZE))

    def test_resizing_snaps_the_dragged_corner(self):
        self.assertEqual(arrange.snap_resize((100, 100, 1612, 600), "se", [WIDE], [(1720, 0, 500, 500)]),
                         (100, 100, 1620, 600))
        self.assertEqual(arrange.snap_resize((6, 100, 600, 600), "sw", [WIDE], []), (0, 100, 606, 600))

    def test_a_window_must_stay_on_a_monitor(self):
        self.assertTrue(arrange.on_screen((3400, 0, 800, 600), [WIDE]))
        self.assertFalse(arrange.on_screen((-900, 0, 800, 600), [WIDE, SIDE]))
        self.assertTrue(arrange.on_screen((5000, 500, 800, 600), [WIDE, SIDE]))


class ViewTests(unittest.TestCase):
    def test_screen_and_canvas_map_both_ways(self):
        view = View(arrange.bounds([WIDE, SIDE]), 760, 430)
        x0, y0, x1, y1 = view.to_canvas(WIDE.area)
        self.assertAlmostEqual(x1 - x0, 3440 * view.scale)
        self.assertLessEqual(x1, 760)
        self.assertEqual(view.to_screen(x0, y0), (0, 0))
        self.assertEqual(view.to_screen(*view.to_canvas(SIDE.area)[2:]), (5360, 1080))
        self.assertGreater(view.distance(8), 8)

    def test_monitors_left_of_the_main_one(self):
        left = Monitor((-1920, 0, 1920, 1080), (-1920, 0, 1920, 1080))
        self.assertEqual(arrange.bounds([WIDE, left]), (-1920, 0, 5360, 1440))
        self.assertEqual(arrange.ordered([WIDE, left])[0], left)
        view = View(arrange.bounds([WIDE, left]), 760, 430)
        self.assertGreaterEqual(view.to_canvas(left.area)[0], 0)


class BesideTests(unittest.TestCase):
    def test_the_next_window_goes_to_the_right(self):
        first = (0, 0, 1280, 720)
        self.assertEqual(arrange.beside(first, [WIDE, SIDE], [first]), (1280, 0, 1280, 720))

    def test_a_taken_or_missing_side_is_skipped(self):
        first, second = (0, 0, 1720, 720), (1720, 0, 1720, 720)
        # right of the second one the monitor ends, so the window goes below
        self.assertEqual(arrange.beside(second, [WIDE], [first, second]), (1720, 720, 1720, 720))
        # right is taken and nothing fits below: left of it
        low = (1720, 720, 1720, 720)
        self.assertEqual(arrange.beside(low, [WIDE], [first, second, low]), (0, 720, 1720, 720))

    def test_without_a_free_side_the_next_free_place_is_taken(self):
        first, second = (0, 0, 1600, 900), (1600, 0, 1600, 900)
        # nothing fits around the second window on the ultrawide: the other monitor is free
        self.assertEqual(arrange.beside(second, [WIDE, SIDE], [first, second]), (3440, 0, 1600, 900))

    def test_no_room_gives_none(self):
        whole = WIDE.area
        self.assertIsNone(arrange.beside(whole, [WIDE], [whole]))
        self.assertFalse(arrange.fits((3000, 0, 1280, 720), [WIDE, SIDE], []))    # would span two monitors


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(__import__("os").name == "nt", "needs Windows")
class WindowsMonitorTests(unittest.TestCase):
    def test_the_monitors_are_read_from_windows(self):
        from fog_launch.windows import WindowsBackend

        found = WindowsBackend().monitors()
        for area, work, primary in found:
            self.assertEqual(len(area), 4)
            self.assertGreater(area[2], 0)
            self.assertGreater(area[3], 0)
            self.assertTrue(arrange.overlaps(area, work) or area == work)
            self.assertIsInstance(primary, bool)
        if found:
            self.assertEqual(sum(primary for _a, _w, primary in found), 1)

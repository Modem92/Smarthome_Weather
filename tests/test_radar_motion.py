"""Offline motion, geometry, transport and worker lifecycle regression tests."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from wetterstation.maps.radar_map import RadarMapResult, RadarMapClient, RadarMapError, MapPosition, RADAR_URL
from wetterstation.maps.radar_motion import (analyse_motion, fresh_source, usable_pair, RainVector, RadarMotion,
                          project_vectors, _classes)
from wetterstation.maps.radar_render import DWD_STRENGTHS


def pattern(seed=42, size=(50, 29), region=(8, 5, 42, 24)):
    image = Image.new("RGBA", size)
    generator = random.Random(seed)
    colors = list(DWD_STRENGTHS)
    for y in range(region[1], region[3]):
        for x in range(region[0], region[2]):
            if generator.random() < .8:
                image.putpixel((x, y), (*colors[generator.randrange(9)], 255))
    return image


def png(image, scale=10):
    output = BytesIO()
    image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST).save(output, "PNG")
    return output.getvalue()


def pair(dx=2, dy=0, image=None):
    image = pattern() if image is None else image
    moved = Image.new("RGBA", image.size)
    moved.paste(image, (dx, dy))
    now = datetime.now(timezone.utc)
    old = RadarMapResult(b"", png(image), now - timedelta(minutes=5), now)
    return replace(old, radar=png(moved), observed_at=now), old


class RadarMotionTests(unittest.TestCase):
    def setUp(self):
        guard = patch("wetterstation.maps.radar_map.urllib.request.urlopen", side_effect=AssertionError("No live requests"))
        guard.start()
        self.addCleanup(guard.stop)

    def test_eight_directions_within_fifteen_degrees_and_anchors_in_rain(self):
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, 2), (2, -2), (-2, -2)):
            with self.subTest(direction=(dx, dy)):
                current, older = pair(dx, dy)
                result = analyse_motion(current, older)
                self.assertTrue(result.vectors)
                self.assertIs(result.source, current)
                self.assertEqual(result.previous_time, older.observed_at)
                for v in result.vectors:
                    cosine = (v.dx * dx + v.dy * dy) / (math.hypot(v.dx, v.dy) * math.hypot(dx, dy))
                    self.assertLessEqual(math.degrees(math.acos(min(1, cosine))), 15)
                    self.assertGreaterEqual(v.confidence, .85)

    def test_stationary_sparse_repeated_unknown_and_new_patterns_have_no_vectors(self):
        checker = Image.new("RGBA", (50, 29))
        colors = list(DWD_STRENGTHS)
        for y in range(29):
            for x in range(50):
                checker.putpixel((x, y), (*colors[(x + y) % 2 * 7], 255))
        sparse = Image.new("RGBA", (50, 29))
        sparse.putpixel((20, 10), (*colors[5], 255))
        for image, dx in ((pattern(), 0), (checker, 2), (sparse, 2),
                          (Image.new("RGBA", (50, 29), (125, 125, 125, 255)), 2),
                          (Image.new("RGBA", (50, 29), (45, 23, 81, 255)), 2)):
            current, older = pair(dx, 0, image)
            self.assertFalse(analyse_motion(current, older).vectors)
        current, older = pair()
        for old, new in ((png(pattern(99)), current.radar), (png(Image.new("RGBA", (50, 29))), current.radar),
                         (older.radar, png(Image.new("RGBA", (50, 29))))):
            self.assertFalse(analyse_motion(replace(current, radar=new), replace(older, radar=old)).vectors)

    def test_intensity_changes_preserve_direction(self):
        image = pattern()
        brighter = image.copy()
        colors = list(DWD_STRENGTHS)
        for y in range(image.height):
            for x in range(image.width):
                color = image.getpixel((x, y))
                if color[3]:
                    brighter.putpixel((x, y), (*colors[colors.index(color[:3]) + 1], 255))
        current, older = pair(image=brighter)
        older = replace(older, radar=png(image))
        vectors = analyse_motion(current, older).vectors
        self.assertTrue(vectors)
        self.assertTrue(all(v.dx > 0 and abs(v.dy) < .1 for v in vectors))

    def test_two_regions_move_in_opposite_directions(self):
        size = (82, 29)
        left = pattern(42, size, (7, 5, 29, 24))
        right = pattern(71, size, (53, 5, 75, 24))
        old = Image.alpha_composite(left, right)
        new = Image.new("RGBA", size)
        new.alpha_composite(left, (2, 0))
        new.alpha_composite(right, (-2, 0))
        current, older = pair(image=old)
        result = analyse_motion(replace(current, radar=png(new)), older)
        self.assertTrue(any(v.dx > 0 and v.x < 410 for v in result.vectors))
        self.assertTrue(any(v.dx < 0 and v.x > 410 for v in result.vectors))

    def test_time_place_staleness_and_standby_gates(self):
        current, older = pair()
        for previous in (current, replace(older, observed_at=current.observed_at - timedelta(minutes=15)),
                         replace(older, position=MapPosition("Berlin", "Berlin", 52.52, 13.405))):
            self.assertFalse(usable_pair(current, previous))
            with self.assertRaises(ValueError):
                analyse_motion(current, previous)
        self.assertTrue(usable_pair(current, replace(older, observed_at=current.observed_at - timedelta(minutes=10))))
        self.assertTrue(analyse_motion(current, replace(older, observed_at=current.observed_at - timedelta(minutes=10))).vectors)
        for source in (replace(current, stale=True),
                       replace(current, observed_at=current.observed_at - timedelta(minutes=16)),
                       replace(current, observed_at=current.observed_at + timedelta(minutes=1))):
            self.assertFalse(fresh_source(source))
            with self.assertRaises(ValueError):
                analyse_motion(source, older)

    def test_all_raw_classes_remain_distinct_and_missing_pixels_are_masked(self):
        colors = list(DWD_STRENGTHS)
        image = Image.new("RGBA", (len(colors) + 3, 1))
        for i, color in enumerate(colors):
            image.putpixel((i, 0), (*color, 255))
        image.putpixel((len(colors), 0), (125, 125, 125, 255))
        image.putpixel((len(colors) + 1, 0), (12, 34, 56, 255))
        strength, mask = _classes(png(image, 1))
        values = [strength.getpixel((i, 0)) for i in range(len(colors))]
        self.assertEqual(values, sorted(set(values)))
        self.assertTrue(all(mask.getpixel((i, 0)) == 255 for i in range(len(colors))))
        self.assertEqual(mask.getpixel((len(colors), 0)), 0)
        self.assertEqual(mask.getpixel((len(colors) + 1, 0)), 0)
        self.assertEqual(mask.getpixel((len(colors) + 2, 0)), 255)

    def test_restart_reuses_previous_disk_observation_before_manifest_replacement(self):
        current, older = pair()
        base = png(Image.new("RGB", (50, 29), "white"))
        current, older = replace(current, basemap=base), replace(older, basemap=base)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            previous_client = RadarMapClient(cache_dir=directory)
            key = previous_client._cache_key(500, 290, older.position)
            previous_client._write_cache(key, older, 500, 290)
            client = RadarMapClient(cache_dir=directory)
            with patch.object(client, "_radar_timestamp", return_value=current.observed_at), patch.object(
                    client, "_request", side_effect=(base, current.radar)) as request:
                live = client.fetch(500, 290, current.position)
                comparison = client.fetch_previous(live)
                self.assertEqual(comparison.observed_at, older.observed_at)
                self.assertEqual(request.call_count, 2)
                self.assertEqual(client._read_cache(key, 500, 290, live.position).observed_at, live.observed_at)

    def test_changed_source_dimensions_share_geographic_overlap(self):
        current, older = pair()
        with Image.open(BytesIO(older.radar)) as image:
            # Wider image has the same geographic height and center, not stretched content.
            wider = Image.new("RGBA", (700, 290))
            wider.paste(image, (100, 0))
        result = analyse_motion(current, replace(older, radar=png(wider, 1)))
        self.assertTrue(result.vectors)
        self.assertTrue(all(v.dx > 0 and abs(v.dy) < .1 for v in result.vectors))

    def test_projection_crop_spacing_three_limit_and_protected_areas(self):
        current, older = pair()
        vectors = tuple(RainVector(x, y, 2, 1, 1) for y in (100, 250, 400)
                        for x in (80, 250, 420, 590, 760, 930))
        motion = RadarMotion(current, older.observed_at, current.observed_at, (1024, 600), vectors)
        for size in ((1024, 600), (480, 800), (360, 300)):
            protected = ((size[0] / 2 - 70, size[1] / 2 - 70, size[0] / 2 + 70, size[1] / 2 + 20),)
            arrows = project_vectors(motion, size, protected=protected)
            self.assertLessEqual(len(arrows), 3)
            for x1, y1, x2, y2 in arrows:
                scale = max(.8, min(size[0] / 1024, size[1] / 600))
                self.assertAlmostEqual(math.hypot(x2 - x1, y2 - y1), 44 * scale)
                self.assertTrue(0 <= x1 <= size[0] and 0 <= x2 <= size[0])
                self.assertTrue(0 <= y1 <= size[1] and 0 <= y2 <= size[1])
                self.assertGreater(x2, x1)
                self.assertGreater(y2, y1)
        center = replace(motion, vectors=(RainVector(512, 300, 1, 0, 1),))
        x1, y1, x2, y2 = project_vectors(center, (480, 800))[0]
        self.assertAlmostEqual((x1 + x2) / 2, 240)
        self.assertAlmostEqual((y1 + y2) / 2, 400)

    def test_previous_transport_only_radar_and_no_current_cache_mutation(self):
        current, older = pair()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            client = RadarMapClient(cache_dir=directory)
            client._radar_available_from = current.observed_at - timedelta(days=1)
            with patch.object(client, "_request", return_value=older.radar) as request, patch.object(client, "_write_cache") as write:
                result = client.fetch_previous(current)
                self.assertEqual(request.call_count, 1)
                url = request.call_args.args[0]
                self.assertTrue(url.startswith(RADAR_URL))
                args = parse_qs(urlsplit(url).query)
                self.assertEqual(args["LAYERS"], ["dwd:Radar_wn-analysis_1x1km_ger"])
                self.assertEqual(datetime.fromisoformat(args["TIME"][0].replace("Z", "+00:00")), older.observed_at)
                self.assertEqual(result.fetched_at, current.fetched_at)
                self.assertIs(result.basemap, current.basemap)
                write.assert_not_called()
                request.reset_mock()
                self.assertIs(client.fetch_previous(current), result)
                request.assert_not_called()
                client._previous = older
                request.reset_mock()
                self.assertIs(client.fetch_previous(current), older)
                request.assert_not_called()
                client._previous = None
                request.side_effect = TimeoutError("dummy-sensitive")
                with self.assertRaises(RadarMapError) as error:
                    client.fetch_previous(current)
                self.assertNotIn("dummy-sensitive", str(error.exception))
            client._radar_available_from = current.observed_at
            with patch.object(client, "_request") as request:
                with self.assertRaises(RadarMapError):
                    client.fetch_previous(current)
                request.assert_not_called()


if __name__ == "__main__":
    unittest.main()

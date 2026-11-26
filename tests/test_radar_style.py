"""Appearance contracts for local radar rendering; no network or real settings."""
import unittest

from PIL import Image, ImageDraw

from wetterstation.maps.radar_render import (DWD_STRENGTHS, MAX_RADAR_ALPHA, RADAR_COLOR_LUTS,
                          soften_radar, style_basemap)


class RadarStyleTests(unittest.TestCase):
    def test_outer_edge_fades_through_lilac_without_square_boundary(self):
        source = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        ImageDraw.Draw(source).rectangle((80, 40, 175, 215), fill=(0, 153, 52, 255))
        soft = soften_radar(source)
        red, green, blue, alpha = soft.getpixel((70, 128))
        self.assertGreater(alpha, 0)
        self.assertLess(alpha, 25)
        self.assertGreater(blue, red)
        self.assertGreater(red, green)
        self.assertEqual(soft.getpixel((0, 0))[3], 0)
        alphas = [soft.getpixel((x, 128))[3] for x in range(50, 110)]
        self.assertGreater(len(set(alphas)), 20)
        self.assertLess(max(abs(b - a) for a, b in zip(alphas, alphas[1:])), 15)

    def test_dry_and_no_data_images_never_gain_rain(self):
        for color in ((0, 0, 0, 0), (255, 255, 0, 0), (125, 125, 125, 128), (255, 255, 255, 0)):
            with self.subTest(color=color):
                self.assertIsNone(soften_radar(Image.new("RGBA", (128, 128), color)).getchannel("A").getbbox())

    def test_missing_coverage_is_not_filled_from_adjacent_rain(self):
        source = Image.new("RGBA", (256, 256), (0, 153, 52, 255))
        ImageDraw.Draw(source).rectangle((128, 0, 255, 255), fill=(125, 125, 125, 128))
        result = soften_radar(source)
        self.assertEqual(result.getpixel((129, 128))[3], 0)
        self.assertGreater(result.getpixel((125, 128))[3], 0)

    def test_intensity_bands_form_continuous_green_transition(self):
        source = Image.new("RGBA", (256, 256), (0, 202, 202, 255))
        ImageDraw.Draw(source).rectangle((128, 0, 255, 255), fill=(255, 255, 0, 255))
        result = soften_radar(source)
        pixels = [result.getpixel((x, 128)) for x in range(105, 150)]
        self.assertGreater(len(set(pixels)), 20)
        self.assertLess(max(abs(b[c] - a[c]) for a, b in zip(pixels, pixels[1:]) for c in range(3)), 20)
        red, green, blue, _alpha = result.getpixel((128, 128))
        self.assertGreater(green, red)
        self.assertGreater(green, blue)

    def test_every_dwd_class_is_translucent_and_strong_cores_remain_yellow(self):
        for color, strength in DWD_STRENGTHS.items():
            with self.subTest(color=color):
                pixel = soften_radar(Image.new("RGBA", (32, 32), (*color, 255))).getpixel((16, 16))
                self.assertEqual(pixel[3], MAX_RADAR_ALPHA)
                self.assertEqual(pixel[:3], tuple(lut[strength] for lut in RADAR_COLOR_LUTS))
                if strength == 255:
                    self.assertGreater(pixel[0], 240)
                    self.assertGreater(pixel[1], 220)
                    self.assertLess(pixel[2], 70)

    def test_original_alpha_is_respected_and_underlying_map_remains_visible(self):
        source = Image.new("RGBA", (32, 32), (255, 255, 0, 128))
        layer = soften_radar(source)
        self.assertLessEqual(layer.getpixel((16, 16))[3], MAX_RADAR_ALPHA // 2 + 1)
        source = Image.new("RGBA", (32, 32), (255, 255, 0, 255))
        layer = soften_radar(source)
        map_image = Image.new("RGBA", (32, 32), "white")
        ImageDraw.Draw(map_image).line((0, 16, 31, 16), fill="#303030", width=1)
        result = Image.alpha_composite(map_image, layer)
        self.assertGreater(sum(result.getpixel((16, 15))[:3]) - sum(result.getpixel((16, 16))[:3]), 150)

    def test_unknown_upstream_palette_is_rejected_instead_of_fake_dry_weather(self):
        with self.assertRaises(ValueError):
            soften_radar(Image.new("RGBA", (32, 32), (17, 43, 99, 255)))

    def test_basemap_is_warm_with_pale_green_orange_roads_and_gray_sharp_labels(self):
        source = Image.new("RGBA", (6, 1), "white")
        swatches = ((255, 253, 238), (223, 240, 182), (0, 58, 189),
                    (48, 48, 48), (210, 232, 250), (239, 225, 254))
        for x, color in enumerate(swatches):
            source.putpixel((x, 0), (*color, 255))
        result = style_basemap(source)
        background, forest, road, text, water, urban = [result.getpixel((x, 0)) for x in range(6)]
        self.assertTrue(all(value > 230 for value in background[:3]))
        self.assertGreater(forest[1], forest[0])
        self.assertGreater(forest[1], forest[2])
        self.assertGreater(road[0], road[1])
        self.assertGreater(road[1], road[2])
        self.assertLess(max(text[:3]), 90)
        self.assertLess(max(text[:3]) - min(text[:3]), 4)
        self.assertGreater(water[2], water[0])
        self.assertLess(max(urban[:3]) - min(urban[:3]), 20)
        self.assertEqual(result.getchannel("A").getextrema(), (255, 255))


if __name__ == "__main__":
    unittest.main()

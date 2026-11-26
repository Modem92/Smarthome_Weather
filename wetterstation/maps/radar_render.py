"""Prepare aligned map layers without Tk, network access, or persistent storage."""
from dataclasses import dataclass
from io import BytesIO

from wetterstation.maps.radar_map import RadarMapResult, RADAR_LAT_SPAN

# DWD WN WMS ColorMap intervals, verified via GetStyles on 23.10.2026.
# These are display classes, not a conversion from reflectivity to mm/h.
DWD_STRENGTHS = {
    (153, 255, 255): 64, (51, 255, 255): 80, (0, 202, 202): 104,
    (0, 153, 52): 128, (77, 191, 26): 154, (153, 204, 0): 180,
    (204, 230, 0): 205, (255, 255, 0): 232, (255, 196, 0): 255,
    (255, 137, 0): 255, (255, 0, 0): 255, (180, 0, 0): 255,
    (72, 72, 255): 255, (0, 0, 202): 255, (153, 0, 153): 255,
    (255, 51, 255): 255, (0, 0, 0): 255,
}
NO_ECHO_COLORS = {(125, 125, 125), (255, 255, 255), (251, 0, 255)}
SMOOTHING_KM = .65
MAX_RADAR_ALPHA = 158  # 62%; geography remains visible even beneath yellow cores.
RADAR_COLOR_STOPS = (
    (0, (214, 202, 245)), (20, (183, 190, 240)), (45, (105, 202, 233)),
    (80, (48, 207, 204)), (128, (53, 213, 153)), (165, (113, 221, 108)),
    (205, (199, 232, 64)), (235, (244, 238, 40)), (255, (255, 235, 45)),
)


def _radar_color_luts() -> tuple[list[int], list[int], list[int]]:
    colors = []
    for value in range(256):
        for (low, start), (high, end) in zip(RADAR_COLOR_STOPS, RADAR_COLOR_STOPS[1:]):
            if low <= value <= high:
                ratio = (value - low) / (high - low)
                colors.append(tuple(round(a + (b - a) * ratio) for a, b in zip(start, end)))
                break
    return tuple([color[channel] for color in colors] for channel in range(3))


RADAR_COLOR_LUTS = _radar_color_luts()


def style_basemap(image):
    """A warm, restrained street map; keep geometry and label edges sharp."""
    from PIL import Image, ImageChops

    rgb = image.convert("RGB")
    red, green, blue = rgb.split()
    # Tint the cartographic road blues; pale water colors remain blue.
    road_mask = ImageChops.multiply(
        ImageChops.subtract(blue, red).point(lambda v: max(0, min(255, (v - 30) * 3))),
        ImageChops.subtract(blue, green).point(lambda v: max(0, min(255, (v - 45) * 5))))
    rgb = Image.composite(Image.new("RGB", rgb.size, (239, 180, 76)), rgb, road_mask)
    hue, saturation, _value = rgb.convert("HSV").split()
    purple_mask = ImageChops.multiply(hue.point(lambda v: 255 if 175 <= v <= 225 else 0),
                                     saturation.point(lambda v: min(255, max(0, (v - 12) * 12))))
    cream = Image.new("RGB", rgb.size, (250, 248, 239))
    rgb = Image.composite(Image.blend(rgb, cream, .80), rgb, purple_mask)
    return Image.blend(rgb, cream, .12).convert("RGBA")


def soften_radar(image):
    """Interpolate DWD classes and coverage separately, preserving transparent dry areas."""
    from PIL import Image, ImageChops, ImageFilter

    rgba = image.convert("RGBA")
    source_alpha = rgba.getchannel("A")
    if source_alpha.getbbox() is None:
        return Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    indexed = rgba.convert("RGB").quantize(colors=256, dither=Image.Dither.NONE)
    palette = indexed.getpalette()
    strength_lut, coverage_lut = [], []
    for index in range(256):
        color = tuple(palette[index * 3:index * 3 + 3])
        strength_lut.append(DWD_STRENGTHS.get(color, 0))
        coverage_lut.append(255 if color in DWD_STRENGTHS else 0)
    coverage = ImageChops.multiply(indexed.point(coverage_lut, mode="L"), source_alpha)
    if coverage.getbbox() is None:
        used = {tuple(palette[index * 3:index * 3 + 3]) for _count, index in indexed.getcolors()}
        if not used.issubset(NO_ECHO_COLORS | set(DWD_STRENGTHS)):
            raise ValueError("Unbekannte DWD-Farbskala")
        return Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    strength = ImageChops.multiply(indexed.point(strength_lut, mode="L"), source_alpha)
    radius = rgba.height * SMOOTHING_KM / (RADAR_LAT_SPAN * 111.32)
    smooth = strength.filter(ImageFilter.GaussianBlur(radius))
    alpha = coverage.filter(ImageFilter.GaussianBlur(radius)).point(
        lambda value: round(value * MAX_RADAR_ALPHA / 255))
    available = indexed.point([0 if tuple(palette[i * 3:i * 3 + 3]) == (125, 125, 125)
                               else 255 for i in range(256)], mode="L")
    alpha = ImageChops.multiply(alpha, available)
    return Image.merge("RGBA", (*[smooth.point(lut) for lut in RADAR_COLOR_LUTS], alpha))


@dataclass(frozen=True, eq=False)
class RadarRenderRequest:
    result: RadarMapResult
    size: tuple[int, int]
    query: str
    epoch: int

    def matches(self, other: "RadarRenderRequest | None") -> bool:
        # Keep strong references to the source; never hash/compare entire PNGs in the UI.
        return (other is not None and self.size == other.size and self.query == other.query
                and self.epoch == other.epoch and self.result.position == other.result.position
                and self.result.provider == other.result.provider and self.result.coverage is other.result.coverage
                and self.result.basemap is other.result.basemap and self.result.radar is other.result.radar)


def prepare_radar_layers(request: RadarRenderRequest) -> tuple[bytes, bytes]:
    from PIL import Image, ImageOps

    if request.result.provider == "rainviewer":
        from PIL import ImageChops, ImageDraw
        with Image.open(BytesIO(request.result.basemap)) as source:
            base = style_basemap(source)
        with Image.open(BytesIO(request.result.radar)) as source:
            radar = source.convert("RGBA")
            radar.putalpha(radar.getchannel("A").point(lambda v: round(v * MAX_RADAR_ALPHA / 255)))
        with Image.open(BytesIO(request.result.coverage)) as source:
            missing = source.convert("RGBA").getchannel("A")
        # Mask out precipitation where the provider cannot confirm coverage.
        radar.putalpha(ImageChops.multiply(radar.getchannel("A"), ImageChops.invert(missing)))
        hatch = Image.new("RGBA", radar.size, (85, 94, 108, 65))
        draw = ImageDraw.Draw(hatch)
        for x in range(-radar.height, radar.width, 16):
            draw.line((x, 0, x + radar.height, radar.height), fill=(85, 94, 108, 135), width=2)
        hatch.putalpha(ImageChops.multiply(hatch.getchannel("A"), missing))
        radar = Image.alpha_composite(radar, hatch)
        layers = []
        for image in (base, radar):
            scaled = ImageOps.fit(image, request.size, method=Image.Resampling.LANCZOS, centering=(.5, .5))
            with BytesIO() as output:
                scaled.save(output, "PNG")
                layers.append(output.getvalue())
        return tuple(layers)
    layers = []
    for data, process in ((request.result.basemap, style_basemap), (request.result.radar, soften_radar)):
        with Image.open(BytesIO(data)) as image:
            scaled = ImageOps.fit(process(image), request.size,
                                  method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            with BytesIO() as output:
                scaled.save(output, format="PNG")
                layers.append(output.getvalue())
    return layers[0], layers[1]

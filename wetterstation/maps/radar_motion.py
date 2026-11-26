"""Conservative local tracking of raw radar classes. No Tk, storage or network."""
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import math

from wetterstation.maps.radar_map import RadarMapClient, RadarMapResult
from wetterstation.maps.radar_render import DWD_STRENGTHS

MAX_MOTION_AGE = 15 * 60
SQUARES = tuple(value * value for value in range(256))


def usable_pair(current: RadarMapResult, previous: RadarMapResult) -> bool:
    return (current.provider == previous.provider == "dwd" and current.position == previous.position
            and (current.observed_at - previous.observed_at).total_seconds() in (300, 600))


def fresh_source(source: RadarMapResult, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return (source.provider == "dwd" and not source.stale and source.observed_at.tzinfo is not None
            and 0 <= (now - source.observed_at).total_seconds() <= MAX_MOTION_AGE)


@dataclass(frozen=True)
class RainVector:
    # Source-image pixel coordinates and displacement (east/right, south/down).
    x: float
    y: float
    dx: float
    dy: float
    confidence: float


@dataclass(frozen=True)
class RadarMotion:
    source: RadarMapResult
    previous_time: datetime
    observed_at: datetime
    source_size: tuple[int, int]
    vectors: tuple[RainVector, ...]


def _classes(data: bytes):
    from PIL import Image, ImageChops
    with Image.open(BytesIO(data)) as opened:
        image = opened.convert("RGBA")
    alpha = image.getchannel("A")
    indexed = image.convert("RGB").quantize(colors=256, dither=Image.Dither.NONE)
    palette = indexed.getpalette()
    levels = {color: (i + 1) * 15 for i, color in enumerate(DWD_STRENGTHS)}
    colors = [tuple(palette[i * 3:i * 3 + 3]) for i in range(256)]
    strength = ImageChops.multiply(indexed.point([levels.get(c, 0) for c in colors], "L"), alpha)
    known = indexed.point([255 if c in levels or c == (255, 255, 255) else 0 for c in colors], "L")
    # Transparent pixels are dry; opaque no-data/unknown palette entries are not dry.
    valid = ImageChops.lighter(known, alpha.point(lambda a: 255 if a == 0 else 0))
    return strength, valid


def _common_grids(current, previous):
    from PIL import Image
    new, new_mask = _classes(current.radar)
    old, old_mask = _classes(previous.radar)
    bounds = [tuple(map(float, RadarMapClient.bbox(*image.size, current.position).split(",")))
              for image in (new, old)]
    west, south = max(b[0] for b in bounds), max(b[1] for b in bounds)
    east, north = min(b[2] for b in bounds), min(b[3] for b in bounds)
    km_lon = 111.32 * math.cos(math.radians(current.position.lat))
    size = (max(1, round((east - west) * km_lon)), max(1, round((north - south) * 111.32)))
    grids = []
    for image, mask, (w, s, e, n) in zip((new, old), (new_mask, old_mask), bounds):
        box = ((west - w) / (e - w) * image.width, (n - north) / (n - s) * image.height,
               (east - w) / (e - w) * image.width, (n - south) / (n - s) * image.height)
        grids.append((image.resize(size, Image.Resampling.BOX, box=box),
                      mask.resize(size, Image.Resampling.BOX, box=box).point(lambda v: 255 if v == 255 else 0)))
    nw, ns, ne, nn = bounds[0]
    # Mapping the common geographic grid back to the unmodified new source image.
    origin = ((west - nw) / (ne - nw) * new.width, (nn - north) / (nn - ns) * new.height)
    step = ((east - west) / (ne - nw) * new.width / size[0],
            (north - south) / (nn - ns) * new.height / size[1])
    return grids[0], grids[1], new.size, origin, step, (north - south) * 111.32 / size[1]


class _Matcher:
    def __init__(self, image, mask):
        from PIL import ImageStat
        self.image, self.mask = image, mask
        self.patches = {}
        for y in range(4, image.height - 4):
            for x in range(4, image.width - 4):
                box = (x - 4, y - 4, x + 5, y + 5)
                if ImageStat.Stat(mask.crop(box)).sum[0] < 81 * 255:
                    continue
                patch = image.crop(box)
                stat = ImageStat.Stat(patch)
                if 81 - patch.histogram()[0] < 8 or stat.stddev[0] < 12:
                    continue
                self.patches[x, y] = patch, stat.sum[0], stat.sum2[0]

    def find(self, template, center, radius):
        from PIL import ImageChops
        patch, total, square = template
        variance = square - total * total / 81
        scores = []
        cx, cy = center
        for y in range(max(4, cy - radius), min(self.image.height - 5, cy + radius) + 1):
            for x in range(max(4, cx - radius), min(self.image.width - 5, cx + radius) + 1):
                other = self.patches.get((x, y))
                if other is None or math.hypot(x - cx, y - cy) > radius:
                    continue
                candidate, other_total, other_square = other
                # These patches have only 81 pixels. Avoid ImageStat's Python scan
                # over a 256-bin histogram for every candidate displacement.
                difference = sum(SQUARES[v] for v in ImageChops.difference(patch, candidate).tobytes())
                cross = (square + other_square - difference) / 2 - total * other_total / 81
                denominator = math.sqrt(max(0, variance * (other_square - other_total * other_total / 81)))
                if denominator:
                    scores.append((cross / denominator, x, y))
        if not scores:
            return None
        scores.sort(reverse=True)
        score, x, y = scores[0]
        rival = max((s for s, xx, yy in scores[1:] if math.hypot(x - xx, y - yy) >= 2), default=-1)
        if score < .85 or score - rival < .08:
            return None
        return score, x, y


def analyse_motion(current: RadarMapResult, previous: RadarMapResult) -> RadarMotion:
    if not fresh_source(current) or not usable_pair(current, previous):
        raise ValueError("Unsuitable radar observations")
    new, old, source_size, origin, step, cell_km = _common_grids(current, previous)
    forward, backward = _Matcher(*old), _Matcher(*new)
    minutes = (current.observed_at - previous.observed_at).total_seconds() / 60
    radius = math.ceil(120 * minutes / 60 / cell_km)
    candidates = []
    for (x, y), template in backward.patches.items():
        if x % 3 or y % 3 or backward.image.getpixel((x, y)) == 0:
            continue
        match = forward.find(template, (x, y), radius)
        if match is None:
            continue
        score, px, py = match
        dx, dy = x - px, y - py
        length = math.hypot(dx, dy)
        if length < 1 or length * cell_km > 120 * minutes / 60:
            continue
        reverse = backward.find(forward.patches[px, py], (px, py), radius)
        if reverse is None or math.hypot(reverse[1] - x, reverse[2] - y) > 1:
            continue
        candidates.append((x, y, dx, dy, min(score, reverse[0])))
    coherent = []
    for x, y, dx, dy, score in candidates:
        length = math.hypot(dx, dy)
        if not any(0 < math.hypot(x - xx, y - yy) <= 10 / cell_km
                   and (dx * ddx + dy * ddy) / (length * math.hypot(ddx, ddy)) >= math.cos(math.pi / 6)
                   and abs(length - math.hypot(ddx, ddy)) <= max(1.5, length * .5)
                   for xx, yy, ddx, ddy, _s in candidates):
            continue
        coherent.append(RainVector(origin[0] + (x + .5) * step[0], origin[1] + (y + .5) * step[1],
                                  dx * step[0], dy * step[1], score))
    return RadarMotion(current, previous.observed_at, current.observed_at, source_size,
                       tuple(sorted(coherent, key=lambda v: v.confidence, reverse=True)))


def project_vectors(motion, target_size, *, offset=(0, 0), protected=()):
    """Match ImageOps.fit's centered proportional crop; select at most three arrows."""
    width, height = target_size
    scale = max(.8, min(width / 1024, height / 600))
    factor = max(width / motion.source_size[0], height / motion.source_size[1])
    crop_x = (motion.source_size[0] * factor - width) / 2
    crop_y = (motion.source_size[1] * factor - height) / 2
    length, margin = 44 * scale, 24 * scale
    arrows = []
    for vector in motion.vectors:
        x = vector.x * factor - crop_x + offset[0]
        y = vector.y * factor - crop_y + offset[1]
        norm = math.hypot(vector.dx, vector.dy)
        if not norm:
            continue
        dx, dy = vector.dx / norm * length / 2, vector.dy / norm * length / 2
        box = (x - abs(dx) - 9 * scale, y - abs(dy) - 9 * scale,
               x + abs(dx) + 9 * scale, y + abs(dy) + 9 * scale)
        if (box[0] < offset[0] + margin or box[1] < offset[1] + margin
                or box[2] > offset[0] + width - margin or box[3] > offset[1] + height - margin):
            continue
        if any(box[0] < r and box[2] > l and box[1] < b and box[3] > t for l, t, r, b in protected):
            continue
        if any(math.hypot(x - (a[0] + a[2]) / 2, y - (a[1] + a[3]) / 2) < 160 * scale for a in arrows):
            continue
        arrows.append((x - dx, y - dy, x + dx, y + dy))
        if len(arrows) == 3:
            break
    return tuple(arrows)

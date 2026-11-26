"""DWD layer-scoped metadata and safe failure messages; no live requests."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from PIL import Image

from wetterstation.maps.radar_map import RadarMapClient, RadarMapError, RADAR_LAYER, RADAR_METADATA_URL


class RadarMetadataTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.folder.cleanup)
        self.client = RadarMapClient(cache_dir=self.folder.name)
        self.now = datetime.now(timezone.utc) - timedelta(minutes=5)
        network = patch("wetterstation.maps.radar_map.urllib.request.urlopen", side_effect=AssertionError("no live requests"))
        network.start()
        self.addCleanup(network.stop)

    def capabilities(self, name=None, default=None):
        name = RADAR_LAYER if name is None else name
        default = self.now.isoformat() if default is None else default
        return (f'<WMS_Capabilities xmlns="http://www.opengis.net/wms"><Capability><Layer>'
            f'<Name>parent</Name><Layer><Name>{name}</Name><Dimension name="time" units="ISO8601" '
            f'default="{default}">2026-01-01T00:00:00Z/{self.now.isoformat()}/PT5M</Dimension>'
            '</Layer></Layer></Capability></WMS_Capabilities>').encode()

    @staticmethod
    def png():
        output = BytesIO()
        Image.new("RGBA", (320, 240), "gray").save(output, format="PNG")
        return output.getvalue()

    def test_scoped_endpoint_accepts_both_exact_radar_layer_names(self):
        for name in (RADAR_LAYER, RADAR_LAYER.split(":", 1)[1]):
            with self.subTest(name=name), patch("wetterstation.maps.radar_map.urllib.request.urlopen", return_value=BytesIO(self.capabilities(name))) as request:
                self.assertEqual(self.client._radar_timestamp(), self.now)
                url = request.call_args.args[0].full_url
                self.assertEqual(urlsplit(url)._replace(query="").geturl(), RADAR_METADATA_URL)
                self.assertEqual(parse_qs(urlsplit(url).query)["REQUEST"], ["GetCapabilities"])
                self.assertEqual(request.call_count, 1)

    def test_current_and_empty_defaults_use_observed_interval_end(self):
        for default in ("current", ""):
            with patch("wetterstation.maps.radar_map.urllib.request.urlopen", return_value=BytesIO(self.capabilities(default=default))):
                self.assertEqual(self.client._radar_timestamp(), self.now)

    def test_other_layers_invalid_xml_future_and_oversized_metadata_are_rejected(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        for data in (self.capabilities(name="other:Radar_wn-analysis_1x1km_ger"), b"<broken",
                     self.capabilities(default=future), b"x" * 2_000_001):
            with self.subTest(data_length=len(data)), patch("wetterstation.maps.radar_map.urllib.request.urlopen", return_value=BytesIO(data)):
                with self.assertRaises((ValueError, ET.ParseError)):
                    self.client._radar_timestamp()

    def test_failures_identify_stage_without_echoing_transport_details(self):
        cases = ((TimeoutError("dummy-sensitive"), None, "DWD-Metadaten"),
                 (None, [TimeoutError("dummy-sensitive")], "Helle Grundkarte"),
                 (None, [self.png(), b"invalid"], "DWD-Radar"))
        for metadata_error, images, expected in cases:
            with self.subTest(stage=expected), patch.object(self.client, "_radar_timestamp", return_value=self.now,
                    side_effect=metadata_error), patch.object(self.client, "_request", side_effect=images):
                with self.assertRaises(RadarMapError) as failure:
                    self.client.fetch(320, 240)
                message = str(failure.exception)
                self.assertIn(expected, message)
                self.assertIn("kein gültiger Karten-Cache", message)
                self.assertNotIn("dummy-sensitive", message)

    def test_metadata_timeout_recovers_valid_cache_without_extra_image_requests(self):
        with patch.object(self.client, "_radar_timestamp", return_value=self.now), patch.object(self.client, "_request", return_value=self.png()):
            original = self.client.fetch(320, 240)
        self.client._memory.clear()
        with patch.object(self.client, "_radar_timestamp", side_effect=TimeoutError("dummy")), patch.object(self.client, "_request") as images:
            recovered = self.client.fetch(320, 240)
        self.assertTrue(recovered.stale)
        self.assertEqual(recovered.basemap, original.basemap)
        images.assert_not_called()


if __name__ == "__main__":
    unittest.main()

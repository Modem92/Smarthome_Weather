"""Headless UI contract check for the clearly marked eight-hour/five-day mock grid."""
import unittest
from unittest.mock import Mock
from datetime import datetime

from wetterstation.ui.app import WeatherPreview
from wetterstation.storage.settings import DisplaySettings
from wetterstation.ui.widgets import new_widget


class MockPreviewUiTests(unittest.TestCase):
    def test_mock_mode_builds_and_draws_eight_hours_and_five_days(self):
        preview = object.__new__(WeatherPreview)
        preview.settings = DisplaySettings()
        preview.mock_preview = True
        preview._load_mock_preview_data()
        self.assertEqual(len(preview.forecast_record.hourly), 8)
        self.assertEqual(len(preview.forecast_record.daily), 5)
        self.assertEqual(preview.forecast_record.source, "DEMO / MOCKDATEN")
        self.assertIn("kein Wetterabruf", preview.forecast_status)

        labels=[]
        def text_block(x,y,text,*_args,**_kwargs):
            labels.append(str(text))
        preview._fit_columns=lambda columns,*_args,**_kwargs:labels.extend(str(row[0]) for column in columns for row in column)
        preview._widget_border_width=2
        preview.canvas=Mock()
        preview._widget_forecast(new_widget("hourly","h"),20,145,950,200)
        preview._widget_forecast(new_widget("daily","d"),20,345,950,200)
        for entry in preview.forecast_record.hourly:
            self.assertIn(datetime.fromisoformat(entry.timestamp).strftime("%H:%M"),labels)
            self.assertIn(f"Regen {entry.precipitation_probability:.0%}",labels)
        self.assertEqual(sum(":" in label for label in labels),8)


if __name__ == "__main__":
    unittest.main(verbosity=2)

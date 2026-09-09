"""
Unit tests for the graphical user interface components (ui/app_window.py).
Tests ScrollableFrame instantiation, session state handling, and layout bindings.
"""

import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from ui.app_window import ScrollableFrame, LeadTimeApp


class TestUIComponents(unittest.TestCase):
    """Test suite for GUI widgets and responsive scrollable container."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root is not None:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def test_scrollable_frame_creation(self):
        """Tests that ScrollableFrame initializes canvas, scrollbar, and inner frame properly."""
        if self.root is None:
            self.skipTest("Tkinter display not available in this environment")

        frame = ScrollableFrame(self.root)
        self.assertIsNotNone(frame.canvas)
        self.assertIsNotNone(frame.scrollbar)
        self.assertIsNotNone(frame.scrollable_content)

        # Add sample child and test mousewheel binding
        lbl = tk.Label(frame.scrollable_content, text="Test Label")
        lbl.pack()
        frame.bind_mousewheel(lbl)
        frame.destroy()

    @patch("ui.app_window.PortalSyncer")
    @patch("ui.app_window.PackageRepository")
    def test_app_session_detection_mocked(self, mock_repo, mock_syncer):
        """Tests that LeadTimeApp sets status badge according to has_shopee_session."""
        if self.root is None:
            self.skipTest("Tkinter display not available in this environment")

        mock_instance = mock_syncer.return_value
        mock_instance.has_shopee_session.return_value = True

        app = LeadTimeApp()
        app.withdraw()

        self.assertTrue(app.refresh_session_status())
        self.assertIn("Conectado", app.lbl_session_status.cget("text"))

        # Test toggling to disconnected
        mock_instance.has_shopee_session.return_value = False
        self.assertFalse(app.refresh_session_status())
        self.assertIn("Pendente", app.lbl_session_status.cget("text"))

        app.destroy()


if __name__ == "__main__":
    unittest.main()

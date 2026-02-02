"""
COM application manager for Office converters.

This module provides singleton COM application instances to avoid
repeatedly opening and closing Office applications (Word, Excel, PowerPoint)
which causes window flickering and performance degradation.
"""

import atexit
import logging
from typing import Any


class ComApplicationManager:
    """
    Manager for COM application instances.

    Maintains singleton instances of Office applications to avoid
    repeatedly creating and destroying them during batch conversion.
    """

    _instance = None
    _lock = None

    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the COM application manager."""
        if self._initialized:
            return

        self.logger = logging.getLogger(__name__)
        self._word_app = None
        self._excel_app = None
        self._powerpoint_app = None
        self._initialized = True

        # Register cleanup on exit
        atexit.register(self.cleanup_all)

    def get_word_app(self) -> Any:
        """
        Get or create Word COM application instance.

        Returns:
            Word application COM object
        """
        # Try to use existing instance if available
        if self._word_app is not None:
            try:
                # Test if the app is still alive by accessing a property
                _ = self._word_app.Name
                return self._word_app
            except Exception:
                # Application crashed or became unavailable, recreate it
                self.logger.warning("Word application became unavailable, recreating...")
                self._word_app = None

        # Create new instance
        try:
            import win32com.client

            self._word_app = win32com.client.Dispatch("Word.Application")
            self._word_app.Visible = False
            self._word_app.DisplayAlerts = False
            self.logger.debug("Created Word COM application instance")
        except Exception as e:
            self.logger.error(f"Failed to create Word application: {e}")
            raise

        return self._word_app

    def get_excel_app(self) -> Any:
        """
        Get or create Excel COM application instance.

        Returns:
            Excel application COM object
        """
        # Try to use existing instance if available
        if self._excel_app is not None:
            try:
                # Test if the app is still alive
                _ = self._excel_app.Name
                return self._excel_app
            except Exception:
                # Application crashed or became unavailable, recreate it
                self.logger.warning("Excel application became unavailable, recreating...")
                self._excel_app = None

        # Create new instance
        try:
            import win32com.client

            self._excel_app = win32com.client.Dispatch("Excel.Application")
            self._excel_app.Visible = False
            self._excel_app.DisplayAlerts = False
            self.logger.debug("Created Excel COM application instance")
        except Exception as e:
            self.logger.error(f"Failed to create Excel application: {e}")
            raise

        return self._excel_app

    def get_powerpoint_app(self) -> Any:
        """
        Get or create PowerPoint COM application instance.

        Returns:
            PowerPoint application COM object
        """
        # Try to use existing instance if available
        if self._powerpoint_app is not None:
            try:
                # Test if the app is still alive
                _ = self._powerpoint_app.Name
                return self._powerpoint_app
            except Exception:
                # Application crashed or became unavailable, recreate it
                self.logger.warning("PowerPoint application became unavailable, recreating...")
                self._powerpoint_app = None

        # Create new instance
        try:
            import win32com.client

            self._powerpoint_app = win32com.client.Dispatch("PowerPoint.Application")
            # Do not force Application.Visible here.
            #
            # In practice, PowerPoint can export to PDF while remaining hidden when the presentation is
            # opened with WithWindow=False, and some Office versions reject setting Visible=0 with
            # "Hiding the application window is not allowed." Forcing Visible=1 causes UI to appear
            # during conversions, so we leave the default as-is and let the strategy handle any
            # format-specific fallbacks if needed.
            self.logger.debug("Created PowerPoint COM application instance")
        except Exception as e:
            self.logger.error(f"Failed to create PowerPoint application: {e}")
            raise

        return self._powerpoint_app

    def cleanup_word(self):
        """Clean up Word COM application."""
        if self._word_app is not None:
            try:
                self._word_app.Quit()
                self._word_app = None
                self.logger.debug("Closed Word COM application")
            except Exception as e:
                self.logger.debug(f"Error closing Word application: {e}")

    def cleanup_excel(self):
        """Clean up Excel COM application."""
        if self._excel_app is not None:
            try:
                self._excel_app.Quit()
                self._excel_app = None
                self.logger.debug("Closed Excel COM application")
            except Exception as e:
                self.logger.debug(f"Error closing Excel application: {e}")

    def cleanup_powerpoint(self):
        """Clean up PowerPoint COM application."""
        if self._powerpoint_app is not None:
            try:
                self._powerpoint_app.Quit()
                self._powerpoint_app = None
                self.logger.debug("Closed PowerPoint COM application")
            except Exception as e:
                self.logger.debug(f"Error closing PowerPoint application: {e}")

    def cleanup_all(self):
        """Clean up all COM applications."""
        self.logger.debug("Cleaning up all COM applications")
        self.cleanup_word()
        self.cleanup_excel()
        self.cleanup_powerpoint()


# Global singleton instance
_com_manager = None


def get_com_manager() -> ComApplicationManager:
    """
    Get the global COM application manager instance.

    Returns:
        Global ComApplicationManager instance
    """
    global _com_manager
    if _com_manager is None:
        _com_manager = ComApplicationManager()
    return _com_manager

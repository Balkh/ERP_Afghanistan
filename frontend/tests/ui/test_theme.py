"""Tests for theme system."""
import pytest
pytest.importorskip("PySide6", reason="PySide6 not available")
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


pytestmark = pytest.mark.theme


class TestThemeManager:
    """Test theme manager functionality."""
    
    def test_theme_manager_exists(self, theme_manager):
        """Theme manager should exist."""
        assert theme_manager is not None
    
    def test_default_theme_is_light(self, theme_manager):
        """Default theme should be light."""
        assert theme_manager.current_theme() == "light"
    
    def test_theme_manager_has_light_theme(self, theme_manager):
        """Theme manager should have light theme."""
        assert "light" in theme_manager._themes
    
    def test_theme_manager_has_dark_theme(self, theme_manager):
        """Theme manager should have dark theme."""
        assert "dark" in theme_manager._themes


class TestThemeSwitching:
    """Test theme switching functionality."""
    
    def test_set_light_theme(self, theme_manager, qapp):
        """Should be able to set light theme."""
        theme_manager.set_theme("light")
        assert theme_manager.current_theme() == "light"
    
    def test_set_dark_theme(self, theme_manager, qapp):
        """Should be able to set dark theme."""
        theme_manager.set_theme("dark")
        assert theme_manager.current_theme() == "dark"
    
    def test_invalid_theme_raises_error(self, theme_manager):
        """Setting invalid theme should raise error."""
        with pytest.raises(ValueError):
            theme_manager.set_theme("invalid_theme")
    
    def test_theme_changed_signal_emits(self, theme_manager):
        """Theme changed signal should emit when theme changes."""
        received = []
        theme_manager.theme_changed.connect(lambda t: received.append(t))
        
        theme_manager.set_theme("dark")
        QTest.qWait(50)
        
        assert "dark" in received


class TestThemeColors:
    """Test theme colors."""
    
    def test_light_theme_colors(self, theme_manager):
        """Light theme should have correct colors."""
        colors = theme_manager._themes["light"]
        
        # Background should be white
        assert colors["background"].name() == "#ffffff"
        
        # Foreground should be dark
        assert colors["foreground"].name() == "#212121"
    
    def test_dark_theme_colors(self, theme_manager):
        """Dark theme should have correct colors."""
        colors = theme_manager._themes["dark"]
        
        # Background should be dark
        assert colors["background"].name() == "#212121"
        
        # Foreground should be white
        assert colors["foreground"].name() == "#ffffff"
    
    def test_get_color_returns_color(self, theme_manager):
        """Get color should return a color."""
        color = theme_manager.get_color("primary")
        assert color is not None
        assert color.isValid()
    
    def test_get_color_with_theme_name(self, theme_manager):
        """Get color with specific theme should work."""
        dark_primary = theme_manager.get_color("primary", "dark")
        light_primary = theme_manager.get_color("primary", "light")
        
        assert dark_primary.name() == light_primary.name()


class TestThemeConsistency:
    """Test theme consistency across components."""
    
    def test_both_themes_have_same_roles(self, theme_manager):
        """Both themes should have the same color roles."""
        light_roles = set(theme_manager._themes["light"].keys())
        dark_roles = set(theme_manager._themes["dark"].keys())
        
        assert light_roles == dark_roles
    
    def test_primary_color_same_in_both_themes(self, theme_manager):
        """Primary color should be the same in both themes."""
        light_primary = theme_manager.get_color("primary", "light")
        dark_primary = theme_manager.get_color("primary", "dark")
        
        assert light_primary.name() == dark_primary.name()
    
    def test_secondary_color_same_in_both_themes(self, theme_manager):
        """Secondary color should be the same in both themes."""
        light_secondary = theme_manager.get_color("secondary", "light")
        dark_secondary = theme_manager.get_color("secondary", "dark")
        
        assert light_secondary.name() == dark_secondary.name()


class TestThemeStylesheet:
    """Test theme stylesheet generation."""
    
    def test_generate_stylesheet_returns_string(self, theme_manager):
        """Generate stylesheet should return a string."""
        theme = theme_manager._themes["light"]
        stylesheet = theme_manager._generate_stylesheet(theme)
        
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
    
    def test_stylesheet_contains_background_color(self, theme_manager):
        """Stylesheet should contain background color."""
        theme = theme_manager._themes["light"]
        stylesheet = theme_manager._generate_stylesheet(theme)
        
        assert "background-color" in stylesheet
    
    def test_stylesheet_contains_button_styles(self, theme_manager):
        """Stylesheet should contain button styles."""
        theme = theme_manager._themes["light"]
        stylesheet = theme_manager._generate_stylesheet(theme)
        
        assert "QPushButton" in stylesheet
    
    def test_dark_theme_stylesheet_dark_background(self, theme_manager):
        """Dark theme stylesheet should have dark background."""
        theme = theme_manager._themes["dark"]
        stylesheet = theme_manager._generate_stylesheet(theme)
        
        assert "#212121" in stylesheet
    
    def test_light_theme_stylesheet_light_background(self, theme_manager):
        """Light theme stylesheet should have light background."""
        theme = theme_manager._themes["light"]
        stylesheet = theme_manager._generate_stylesheet(theme)
        
        assert "#ffffff" in stylesheet
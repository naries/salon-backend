from fastapi import APIRouter
from app.core.customization import (
    LAYOUT_PATTERNS,
    CLIENT_THEMES,
    get_layout_patterns,
    get_client_themes
)

router = APIRouter()


@router.get("/layout-patterns")
def get_all_layout_patterns():
    """Get all available layout patterns with details"""
    return {
        "patterns": LAYOUT_PATTERNS
    }


@router.get("/client-themes")
def get_all_client_themes():
    """Get all available client themes with details"""
    return {
        "themes": CLIENT_THEMES
    }


@router.get("/customization-options")
def get_customization_options():
    """Get all customization options (layouts and themes)"""
    return {
        "layout_patterns": LAYOUT_PATTERNS,
        "client_themes": CLIENT_THEMES
    }

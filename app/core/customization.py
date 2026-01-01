"""
Web Client Customization Constants
Layout patterns and themes for the salon web client
"""

# Layout Patterns
LAYOUT_PATTERNS = {
    "classic": {
        "name": "Classic",
        "description": "Traditional vertical layout with sidebar navigation",
        "features": [
            "Sidebar with logo and navigation",
            "Main content area with service cards",
            "Footer with contact info",
            "Best for desktop users"
        ]
    },
    "modern": {
        "name": "Modern",
        "description": "Clean horizontal layout with top navigation bar",
        "features": [
            "Fixed header with logo and menu",
            "Hero section with call-to-action",
            "Grid-based service display",
            "Mobile-first responsive design"
        ]
    },
    "minimal": {
        "name": "Minimal",
        "description": "Simplified single-page layout with minimal elements",
        "features": [
            "Centered logo and title",
            "Simple service list",
            "One-click booking focus",
            "Ultra-fast loading"
        ]
    },
    "compact": {
        "name": "Compact",
        "description": "Dense layout for quick browsing and booking",
        "features": [
            "Compact service cards",
            "Inline booking forms",
            "Sticky navigation bar",
            "Optimized for quick actions"
        ]
    },
    "elegant": {
        "name": "Elegant",
        "description": "Luxurious layout with animations and transitions",
        "features": [
            "Full-width hero images",
            "Smooth scroll animations",
            "Elegant typography",
            "Premium feel for high-end salons"
        ]
    }
}

# Web Client Themes (different from backoffice themes)
CLIENT_THEMES = {
    "ocean": {
        "name": "Ocean Breeze",
        "primary": "#0891b2",  # Cyan
        "primaryLight": "#06b6d4",
        "primaryDark": "#0e7490",
        "accent": "#06b6d4",
        "background": "#f0fdfa",
        "surface": "#ffffff",
        "text": "#134e4a",
        "textSecondary": "#5f9ea0",
        "border": "#99f6e4",
        "category": "Cool"
    },
    "sunset": {
        "name": "Sunset Glow",
        "primary": "#f97316",  # Orange
        "primaryLight": "#fb923c",
        "primaryDark": "#ea580c",
        "accent": "#fbbf24",
        "background": "#fff7ed",
        "surface": "#ffffff",
        "text": "#7c2d12",
        "textSecondary": "#c2410c",
        "border": "#fed7aa",
        "category": "Warm"
    },
    "lavender": {
        "name": "Lavender Dream",
        "primary": "#a855f7",  # Purple
        "primaryLight": "#c084fc",
        "primaryDark": "#9333ea",
        "accent": "#d946ef",
        "background": "#faf5ff",
        "surface": "#ffffff",
        "text": "#581c87",
        "textSecondary": "#7e22ce",
        "border": "#e9d5ff",
        "category": "Vibrant"
    },
    "forest": {
        "name": "Forest Green",
        "primary": "#16a34a",  # Green
        "primaryLight": "#22c55e",
        "primaryDark": "#15803d",
        "accent": "#84cc16",
        "background": "#f0fdf4",
        "surface": "#ffffff",
        "text": "#14532d",
        "textSecondary": "#166534",
        "border": "#bbf7d0",
        "category": "Natural"
    },
    "rose": {
        "name": "Rose Garden",
        "primary": "#e11d48",  # Rose
        "primaryLight": "#f43f5e",
        "primaryDark": "#be123c",
        "accent": "#fb7185",
        "background": "#fff1f2",
        "surface": "#ffffff",
        "text": "#881337",
        "textSecondary": "#9f1239",
        "border": "#fecdd3",
        "category": "Romantic"
    },
    "midnight": {
        "name": "Midnight Blue",
        "primary": "#1e40af",  # Blue
        "primaryLight": "#3b82f6",
        "primaryDark": "#1e3a8a",
        "accent": "#60a5fa",
        "background": "#eff6ff",
        "surface": "#ffffff",
        "text": "#1e3a8a",
        "textSecondary": "#1e40af",
        "border": "#bfdbfe",
        "category": "Professional"
    },
    "champagne": {
        "name": "Champagne Gold",
        "primary": "#d97706",  # Amber
        "primaryLight": "#f59e0b",
        "primaryDark": "#b45309",
        "accent": "#fbbf24",
        "background": "#fffbeb",
        "surface": "#ffffff",
        "text": "#78350f",
        "textSecondary": "#92400e",
        "border": "#fde68a",
        "category": "Luxury"
    },
    "coral": {
        "name": "Coral Reef",
        "primary": "#ec4899",  # Pink
        "primaryLight": "#f472b6",
        "primaryDark": "#db2777",
        "accent": "#f9a8d4",
        "background": "#fdf2f8",
        "surface": "#ffffff",
        "text": "#831843",
        "textSecondary": "#9d174d",
        "border": "#fbcfe8",
        "category": "Playful"
    }
}

def get_layout_patterns():
    """Get all available layout patterns"""
    return list(LAYOUT_PATTERNS.keys())

def get_layout_pattern_info(pattern_name):
    """Get detailed information about a layout pattern"""
    return LAYOUT_PATTERNS.get(pattern_name)

def get_client_themes():
    """Get all available client themes"""
    return list(CLIENT_THEMES.keys())

def get_client_theme_info(theme_name):
    """Get detailed information about a client theme"""
    return CLIENT_THEMES.get(theme_name)

def validate_layout_pattern(pattern_name):
    """Validate if a layout pattern exists"""
    return pattern_name in LAYOUT_PATTERNS

def validate_client_theme(theme_name):
    """Validate if a client theme exists"""
    return theme_name in CLIENT_THEMES

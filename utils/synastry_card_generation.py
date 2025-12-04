"""
Synastry Poster Generator - Premium Astrological Compatibility Visualization

This module generates elegant SVG-based compatibility posters for synastry analysis.

Key Features:
    - Dynamic Risk Meter (Gauge):
        * Maps overall_score (0-100) to needle rotation angle
        * Score 100: needle points to "SAFE" (left)
        * Score 0: needle points to "HIGH RISK" (right)
    
    - Dynamic Relationship Posture Visual:
        * Score < 45%: "HIGH RISK" bar glows with bold emphasis
        * Score 45-75%: "CAUTION" bar lights up
        * Score > 75%: "SAFE" bar lights up
    
    - Dynamic Elemental Radar Chart:
        * Visualizes elemental balance (Fire, Earth, Air, Water) for both individuals
        * Takes normalized values (0.0 to 1.0) and calculates polygon coordinates
        * Overlays both profiles for easy comparison

Author: Astro Vision
Version: 1.0
"""
import sys
import os
# Ensure project root is on sys.path when running as a script (python services/synastry.py)
_HERE = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
    
import math

from services.synastry_services import calculate_synastry

class SynastryPosterGenerator:
    def __init__(self):
        # Premium Color Palette
        self.colors = {
            "bg": "#121212",  # Charcoal/Black
            "gold_light": "#F6E27A",
            "gold_mid": "#D4AF37",
            "gold_dark": "#AA8020",
            "text_white": "#F0F0F0",
            "text_grey": "#A0A0A0",
            "risk_red": "#8B0000",
            "safe_green": "#006400"
        }
        
        # Dimensions
        self.width = 800
        self.height = 1400
        self.cx = self.width / 2

    def _get_gradients_and_filters(self):
        """Defines the gold gradients and glow effects."""
        return f"""
        <defs>
            <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:{self.colors['gold_dark']};stop-opacity:1" />
                <stop offset="50%" style="stop-color:{self.colors['gold_light']};stop-opacity:1" />
                <stop offset="100%" style="stop-color:{self.colors['gold_dark']};stop-opacity:1" />
            </linearGradient>
            <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        """

    def _draw_radar_chart(self, cx, cy, radius, data_p1, data_p2):
        """Generates the SVG path for the elemental radar chart."""
        # Axes: 0=Fire(Top), 1=Earth(Right), 2=Air(Left), 3=Water(Bottom)
        # Note: Usually Air is opposite Fire, but following user prompt order roughly.
        # Let's do: Top(Fire), Right(Earth), Bottom(Water), Left(Air)
        
        def get_point(value, axis_idx):
            # value is 0.0 to 1.0
            r = radius * value
            if axis_idx == 0: return (cx, cy - r) # Top
            if axis_idx == 1: return (cx + r, cy) # Right
            if axis_idx == 2: return (cx, cy + r) # Bottom
            if axis_idx == 3: return (cx - r, cy) # Left
            return (cx, cy)

        # Draw Background Grid
        grid_svg = ""
        for i in [0.25, 0.5, 0.75, 1.0]:
            pts = [get_point(i, 0), get_point(i, 1), get_point(i, 2), get_point(i, 3)]
            d = f"M {pts[0][0]},{pts[0][1]} L {pts[1][0]},{pts[1][1]} L {pts[2][0]},{pts[2][1]} L {pts[3][0]},{pts[3][1]} Z"
            grid_svg += f'<path d="{d}" stroke="{self.colors["gold_dark"]}" stroke-width="1" fill="none" opacity="0.3" />'

        # Helper to draw profile shape
        def make_shape(vals, color, stroke_type):
            pts = [get_point(vals['fire'], 0), get_point(vals['earth'], 1), 
                   get_point(vals['water'], 2), get_point(vals['air'], 3)]
            d = f"M {pts[0][0]},{pts[0][1]} L {pts[1][0]},{pts[1][1]} L {pts[2][0]},{pts[2][1]} L {pts[3][0]},{pts[3][1]} Z"
            return f'<path d="{d}" stroke="{color}" stroke-width="2" fill="{color}" fill-opacity="0.1" stroke-dasharray="{stroke_type}" />'

        p1_shape = make_shape(data_p1, self.colors['gold_light'], "0")
        p2_shape = make_shape(data_p2, "#FFFFFF", "4,2")

        # Labels
        labels = f"""
            <text x="{cx}" y="{cy-radius-15}" text-anchor="middle" fill="{self.colors['gold_mid']}" font-size="12">FIRE</text>
            <text x="{cx+radius+25}" y="{cy+4}" text-anchor="middle" fill="{self.colors['gold_mid']}" font-size="12">EARTH</text>
            <text x="{cx}" y="{cy+radius+20}" text-anchor="middle" fill="{self.colors['gold_mid']}" font-size="12">WATER</text>
            <text x="{cx-radius-25}" y="{cy+4}" text-anchor="middle" fill="{self.colors['gold_mid']}" font-size="12">AIR</text>
        """

        return f"""
        <g>
            {grid_svg}
            {p1_shape}
            {p2_shape}
            {labels}
            <rect x="{cx-70}" y="{cy+radius+40}" width="10" height="2" fill="{self.colors['gold_light']}" />
            <text x="{cx-55}" y="{cy+radius+44}" fill="#AAA" font-size="10">Person 1</text>
            <rect x="{cx+10}" y="{cy+radius+40}" width="10" height="2" fill="#FFF" />
            <text x="{cx+25}" y="{cy+radius+44}" fill="#AAA" font-size="10">Person 2</text>
        </g>
        """

    def _draw_gauge(self, cx, cy, radius, score):
        """Draws the semicircle gauge and rotates needle based on score."""
        # Score 0 to 100.
        # Angles: Left (Safe) = -90deg, Right (High Risk) = 90deg.
        # IMPORTANT: The prompt says Left is SAFE, Right is HIGH RISK.
        # Usually 0% compatibility is HIGH RISK. 
        # So: Score 0 = Right (+90deg), Score 100 = Left (-90deg).
        
        # Mapping score to angle:
        # Score 0 -> +90
        # Score 100 -> -90
        angle = 90 - (score / 100 * 180)
        
        # Draw Arc
        path_d = f"M {cx-radius},{cy} A {radius},{radius} 0 0,1 {cx+radius},{cy}"
        
        return f"""
        <g transform="translate(0, 0)">
            <path d="{path_d}" fill="none" stroke="#333" stroke-width="15" stroke-linecap="round" />
            <path d="{path_d}" fill="none" stroke="url(#goldGradient)" stroke-width="4" stroke-linecap="round" filter="url(#softGlow)" />
            
            <text x="{cx-radius}" y="{cy+25}" text-anchor="middle" fill="{self.colors['gold_mid']}" font-size="12">SAFE</text>
            <text x="{cx+radius}" y="{cy+25}" text-anchor="middle" fill="{self.colors['gold_mid']}" font-size="12">HIGH RISK</text>
            
            <g transform="translate({cx},{cy}) rotate({angle})">
                <line x1="0" y1="0" x2="0" y2="{-radius+10}" stroke="{self.colors['text_white']}" stroke-width="3" />
                <circle cx="0" cy="0" r="6" fill="{self.colors['gold_light']}" />
            </g>
            
            <text x="{cx}" y="{cy+40}" text-anchor="middle" fill="{self.colors['gold_mid']}" font-size="14" letter-spacing="1">RISK METER</text>
        </g>
        """

    def generate(self, data, filename="output_synastry.svg"):
        """
        data dictionary format:
        {
            "p1_name": "Amit",
            "p2_name": "Riya",
            "overall_score": 31.2,
            "kpi": {"emotional": 0, "communication": 53.4, "chemistry": 38.8},
            "elements_p1": {"fire": 0.8, "earth": 0.3, "air": 0.5, "water": 0.2},
            "elements_p2": {"fire": 0.2, "earth": 0.7, "air": 0.4, "water": 0.6},
            "quote": "...",
            "summary": "..."
        }
        """
        
        # Determine Status for Posture Visual
        score = data['overall_score']
        status_safe_op = 0.2
        status_caution_op = 0.2
        status_risk_op = 0.2
        
        if score > 75: status_safe_op = 1.0
        elif score > 45: status_caution_op = 1.0
        else: status_risk_op = 1.0

        svg_content = f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">
            {self._get_gradients_and_filters()}
            
            <rect width="100%" height="100%" fill="{self.colors['bg']}" />
            
            <rect x="20" y="20" width="{self.width-40}" height="{self.height-40}" fill="none" stroke="{self.colors['gold_dark']}" stroke-width="1" opacity="0.3" rx="20" />
            
            <text x="{self.cx}" y="100" text-anchor="middle" font-family="serif" font-size="36" fill="{self.colors['text_white']}">
                Synastry Compatibility — {data['p1_name']} × {data['p2_name']}
            </text>
            <text x="{self.cx}" y="130" text-anchor="middle" font-family="sans-serif" font-size="14" fill="{self.colors['text_grey']}">
                A deep dive into the energetic dynamics and growth potential.
            </text>
            
            <line x1="{self.cx-100}" y1="150" x2="{self.cx+100}" y2="150" stroke="{self.colors['gold_dark']}" opacity="0.5" />

            <g transform="translate({self.cx-150}, 180)">
                <rect width="300" height="120" rx="15" fill="none" stroke="url(#goldGradient)" stroke-width="2" filter="url(#softGlow)" />
                <text x="150" y="75" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="60" fill="{self.colors['text_white']}">
                    {data['overall_score']}%
                </text>
                <text x="150" y="100" text-anchor="middle" font-family="sans-serif" font-size="14" fill="{self.colors['gold_mid']}" text-transform="uppercase" letter-spacing="2">
                    Overall Compatibility
                </text>
            </g>

            <foreignObject x="100" y="330" width="600" height="100">
                <div xmlns="http://www.w3.org/1999/xhtml" style="color: #F0F0F0; font-family: serif; font-style: italic; text-align: center; font-size: 18px; line-height: 1.4;">
                    "{data['quote']}"
                </div>
            </foreignObject>

            <foreignObject x="100" y="440" width="600" height="140">
                <div xmlns="http://www.w3.org/1999/xhtml" style="color: #CCC; font-family: sans-serif; text-align: justify; font-size: 14px; line-height: 1.6;">
                    {data['summary']}
                </div>
            </foreignObject>

            <g transform="translate(50, 600)">
                <g transform="translate(0,0)">
                    <rect width="210" height="60" rx="30" fill="#222" stroke="{self.colors['gold_dark']}" />
                    <text x="30" y="35" font-size="20">❤️</text>
                    <text x="65" y="25" fill="{self.colors['text_white']}" font-size="14" font-weight="bold">Emotional</text>
                    <text x="65" y="45" fill="{self.colors['gold_light']}" font-size="14">Score: {data['kpi']['emotional']}%</text>
                </g>
                <g transform="translate(245,0)">
                    <rect width="210" height="60" rx="30" fill="#222" stroke="{self.colors['gold_dark']}" />
                    <text x="30" y="35" font-size="20">🗣</text>
                    <text x="65" y="25" fill="{self.colors['text_white']}" font-size="14" font-weight="bold">Communication</text>
                    <text x="65" y="45" fill="{self.colors['gold_light']}" font-size="14">Score: {data['kpi']['communication']}%</text>
                </g>
                <g transform="translate(490,0)">
                    <rect width="210" height="60" rx="30" fill="#222" stroke="{self.colors['gold_dark']}" />
                    <text x="30" y="35" font-size="20">🔥</text>
                    <text x="65" y="25" fill="{self.colors['text_white']}" font-size="14" font-weight="bold">Chemistry</text>
                    <text x="65" y="45" fill="{self.colors['gold_light']}" font-size="14">Score: {data['kpi']['chemistry']}%</text>
                </g>
            </g>

            <g transform="translate(0, 720)">
                <g transform="translate(200, 150)">
                   {self._draw_radar_chart(0, 0, 90, data['elements_p1'], data['elements_p2'])}
                   <text x="0" y="130" text-anchor="middle" fill="{self.colors['text_white']}" font-size="14">Elemental Balance</text>
                </g>
                
                <g transform="translate(600, 150)">
                   {self._draw_gauge(0, 0, 100, data['overall_score'])}
                </g>
            </g>

            <g transform="translate({self.cx}, 1050)">
                <text x="0" y="-40" text-anchor="middle" fill="{self.colors['text_white']}" font-size="16" letter-spacing="1">RELATIONSHIP POSTURE</text>
                
                <rect x="-200" y="-20" width="400" height="30" rx="5" stroke="{self.colors['gold_dark']}" fill="none" opacity="0.5" />
                <rect x="-200" y="-20" width="400" height="30" rx="5" fill="{self.colors['gold_light']}" opacity="{status_safe_op * 0.2}" />
                <text x="0" y="0" text-anchor="middle" dominant-baseline="middle" fill="{self.colors['text_white']}" opacity="{0.5 + status_safe_op/2}">SAFE</text>
                
                <rect x="-200" y="20" width="400" height="30" rx="5" stroke="{self.colors['gold_dark']}" fill="none" opacity="0.5" />
                <rect x="-200" y="20" width="400" height="30" rx="5" fill="{self.colors['gold_light']}" opacity="{status_caution_op * 0.2}" />
                <text x="0" y="40" text-anchor="middle" dominant-baseline="middle" fill="{self.colors['text_white']}" opacity="{0.5 + status_caution_op/2}">CAUTION</text>

                <rect x="-200" y="60" width="400" height="30" rx="5" stroke="{self.colors['gold_dark']}" fill="none" opacity="0.5" />
                # Highlight if active
                <rect x="-200" y="60" width="400" height="30" rx="5" fill="{self.colors['gold_mid']}" opacity="{status_risk_op}" filter="{ 'url(#softGlow)' if status_risk_op > 0.5 else 'none' }" />
                <text x="0" y="80" text-anchor="middle" dominant-baseline="middle" fill="{ 'black' if status_risk_op > 0.5 else self.colors['text_white']}" font-weight="{ 'bold' if status_risk_op > 0.5 else 'normal' }">HIGH RISK</text>
            </g>
            
            <g transform="translate({self.cx}, 1250)">
                 <path d="M -20,0 Q 0,-20 20,0 Q 0,20 -20,0 Z" fill="none" stroke="{self.colors['gold_mid']}" stroke-width="2" />
                 <circle cx="0" cy="0" r="5" fill="{self.colors['gold_mid']}" />
                 
                 <text x="0" y="30" text-anchor="middle" font-family="serif" font-size="18" fill="{self.colors['text_white']}" letter-spacing="2">ASTRO VISION</text>
                 <text x="0" y="50" text-anchor="middle" font-family="sans-serif" font-size="10" fill="{self.colors['text_grey']}">Premium Astrological Intelligence</text>
                 
                 <line x1="-50" y1="70" x2="50" y2="70" stroke="{self.colors['gold_dark']}" opacity="0.5" />
                 <text x="0" y="90" text-anchor="middle" font-family="sans-serif" font-size="12" fill="{self.colors['gold_mid']}">Discover more insights</text>
            </g>

        </svg>
        """
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"Generated {filename}")

# ==========================================
# HOW TO USE
# ==========================================
if __name__ == "__main__":
    sample = {
        "person1": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.0760,
            "longitude": 72.8777,
        },
        "person2": {
            "name": "Riya",
            "dateOfBirth": "1993-02-20",
            "timeOfBirth": "06:10:00",
            "placeOfBirth": "Delhi, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 28.6139,
            "longitude": 77.2090,
        },
    }
    res = calculate_synastry(sample["person1"], sample["person2"])
    import json
    print(json.dumps(res, indent=2))

    # 1. Define your data
    input_data = {
        "p1_name": res["person1"],
        "p2_name": res["person2"],
        "overall_score": res["total_score_pct"],
        "kpi": {
            "emotional": res["kpi_scores_pct"]["emotional"],
            "communication": res["kpi_scores_pct"]["communication"],
            "chemistry": res["kpi_scores_pct"]["chemistry"]
        },
        "elements_p1": res["person1"]["elements"],
        "elements_p2": res["person2"]["elements"],
        "quote": res["quote"],
        "summary": res["summary"]
    }

    print(f"Input Data: {input_data}")

    # # 2. Run the Generator
    # generator = SynastryPosterGenerator()
    # generator.generate(input_data, "synastry_poster.svg")
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from reportlab.platypus import Paragraph, Spacer

from ..config import ReportConfig
from ..components import section_header
from ..i18n import lang_for_text, section_title, t
from ..schema import ReportJson


def build_appendix_story(data: ReportJson, config: ReportConfig, styles: Dict[str, any], overflow: Dict[str, List[str]] | None = None) -> List:
    story: List = []
    lang = lang_for_text(config.language_mode)
    story.append(section_header(section_title("appendix", config), styles))
    story.append(Spacer(1, 6))

    if config.density == "COMPACT":
        if lang == "EN":
            disclaimers = [
                "This report is for guidance only.",
                "Use your judgment before acting.",
                "Astrology suggests possibilities, not certainties.",
            ]
            how_to = [
                "Timeline cards show major aspects with start, peak, and end.",
                "Action points suggest practical steps for the day.",
                "Life Areas highlight where effects are strongest.",
                "Badges indicate overall tone of each aspect.",
                "Use this summary to plan mindfully.",
            ]
        else:
            disclaimers = [
                "यह रिपोर्ट केवल मार्गदर्शन के लिए है।",
                "किसी निर्णय से पहले अपने विवेक का उपयोग करें।",
                "ज्योतिष संभावनाएँ दिखाता है, निश्चितता नहीं।",
            ]
            how_to = [
                "समयरेखा कार्ड मुख्य योग और उनके समय दिखाते हैं।",
                "कार्रवाई बिंदु व्यावहारिक कदम सुझाते हैं।",
                "जीवन क्षेत्र बताता है कि असर कहाँ अधिक होगा।",
                "बैज से योग का सामान्य स्वभाव दिखता है।",
                "इसे संक्षिप्त मार्गदर्शन की तरह उपयोग करें।",
            ]
        for line in disclaimers:
            story.append(Paragraph(line, styles["body"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph(t("how_to_read", lang), styles["subheader"]))
        for line in how_to:
            story.append(Paragraph(f"• {line}", styles["body"]))
    else:
        story.append(
            Paragraph(
                "यह रिपोर्ट ज्योतिषीय संकेतों का सार है और इसे निश्चित भविष्यवाणी के रूप में न लें। ",
                styles["body"],
            )
        )
        story.append(
            Paragraph(
                "किसी भी महत्वपूर्ण निर्णय के लिए पेशेवर सलाह और अपने विवेक का उपयोग करें।",
                styles["body"],
            )
        )
        story.append(Spacer(1, 10))

        story.append(Paragraph(t("how_to_read", lang), styles["subheader"]))
        story.append(
            Paragraph(
                "समयरेखा में प्रत्येक कार्ड एक प्रमुख ग्रह-योग (aspect) का प्रभाव दिखाता है — प्रारंभ, शिखर और समाप्ति के साथ। ",
                styles["body"],
            )
        )
        story.append(
            Paragraph(
                "कार्रवाई अनुभाग में व्यावहारिक कदम हैं; मुख्य क्षेत्र अनुभाग बताता है कि जीवन के किन हिस्सों पर अधिक असर हो सकता है।",
                styles["body"],
            )
        )

        if overflow and config.include_full_appendix:
            story.append(Spacer(1, 12))
            for area, bullets in overflow.items():
                story.append(Paragraph(f"{t('more_details', lang)}: {area}", styles["subheader"]))
                for b in bullets:
                    story.append(Paragraph(f"• {b}", styles["body"]))

    return story

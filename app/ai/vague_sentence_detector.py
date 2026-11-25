from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VagueFinding:
    phrase: str
    category: str
    scene_number: int | None
    location: str  # "narration", "dialogue", "ending", "synopsis"
    context: str
    reason: str


class VagueSentenceDetector:
    """
    Detects empty, vague, and telling-not-showing phrases in Hindi story texts.
    Enforces the strict SHOW, DON'T TELL writing approach required by professional screenwriting.
    """

    # Banned abstract summary phrases when not immediately anchored to concrete sensory events
    BANNED_ABSTRACT_SUMMARIES = [
        # Struggles and hardships mentioned without concrete events
        r"मुश्किलों\s+का\s+सामना\s+करना\s+पड़ा",
        r"परेशानियां\s+बढ़ती\s+(?:चली\s+गईं|गईं)",
        r"हालात\s+बहुत\s+खराब\s+हो\s+गए",
        r"हालात\s+बिगड़ते\s+चले\s+गए",
        r"समस्याओं\s+से\s+गुजरना\s+पड़ा",
        r"परेशानियां\s+झेलनी\s+पड़ीं?",
        r"बहुत\s+संघर्ष\s+करना\s+पड़ा",
        r"दुखों\s+का\s+पहाड़\s+टूट\s+पड़ा",
        r"जिंदगी\s+में\s+तूफान\s+आ\s+गया",
        r"बहुत\s+कुछ\s+सहा",
        r"बहुत\s+बुरा\s+हुआ",
        r"कठिनाइयों\s+का\s+सामना\s+किया",
        r"एक\s+के\s+बाद\s+एक\s+मुसीबतें",
        r"किस्मत\s+ने\s+(?:उसका\s+)?साथ\s+छोड़\s+दिया",
        r"किस्मत\s+रूठ\s+गई",
        # Abstract change summaries instead of concrete events
        r"उसकी\s+जिंदगी\s+बदल\s+गई",
        r"सब\s+कुछ\s+बदल\s+चुका\s+था",
        r"अब\s+उसकी\s+दुनिया\s+पहले\s+जैसी\s+नहीं\s+रही",
        r"जीवन\s+में\s+बड़ा\s+बदलाव\s+आ\s+गया",
        r"उसके\s+लिए\s+सब\s+कुछ\s+बदल\s+गया",
        # Generic filler transitions
        r"समय\s+बीतता\s+गया(?:\s+और)?",
        r"वक़्त\s+बीतता\s+गया",
        r"दिन\s+गुज़रते\s+गए",
        # Cliché atmospheric fillers
        r"चारों\s+तरफ\s+गहरा\s+सन्नाटा\s+पसरा\s+हुआ\s+था",
        r"हवा\s+का\s+हर\s+झोंका\s+किसी\s+अनहोनी\s+का\s+इशारा",
        r"दिल\s+की\s+धड़कनें\s+साफ़\s+सुनाई\s+दे\s+रही\s+थीं",
        r"आँखों\s+के\s+सामने\s+तैरते\s+सवालों\s+का\s+कोई\s+जवाब\s+नहीं",
        r"मन\s+में\s+एक\s+गहरा\s+तूफ़ान\s+उठ\s+रहा\s+था",
        # Vague cop-out endings
        r"और\s+इस\s+तरह\s+उसकी\s+जिंदगी\s+बदल\s+गई",
        r"उसने\s+सब\s+कुछ\s+समझ\s+लिया",
        r"समय\s+के\s+साथ\s+सब\s+ठीक\s+हो\s+गया",
        r"यही\s+जिंदगी\s+की\s+सच्चाई\s+है",
    ]

    def __init__(self) -> None:
        self.compiled_patterns = [
            (re.compile(p, re.IGNORECASE | re.UNICODE), p) for p in self.BANNED_ABSTRACT_SUMMARIES
        ]

    def scan_text(
        self, text: str, location: str = "text", scene_number: int | None = None
    ) -> list[VagueFinding]:
        """Scans a single string for banned vague phrases."""
        findings: list[VagueFinding] = []
        if not text:
            return findings

        for pattern, raw_p in self.compiled_patterns:
            for match in pattern.finditer(text):
                matched_str = match.group(0)
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].strip()

                findings.append(
                    VagueFinding(
                        phrase=matched_str,
                        category="vague_telling_not_showing",
                        scene_number=scene_number,
                        location=location,
                        context=f"...{context}...",
                        reason=(
                            f"Vague assertion '{matched_str}' replaces real scene storytelling. "
                            f"Must show exact concrete event (who, what, where, action, dialogue, consequence)."
                        ),
                    )
                )
        return findings

    def audit_scene(self, scene: dict[str, Any]) -> list[VagueFinding]:
        """Audits a scene's narration and dialogue lines for vague storytelling."""
        findings: list[VagueFinding] = []
        scene_num = scene.get("scene_number", 0)

        # Audit narration
        narration = scene.get("narration") or ""
        findings.extend(self.scan_text(narration, location="narration", scene_number=scene_num))

        # Audit dialogue
        for d in scene.get("dialogue") or []:
            if isinstance(d, dict):
                line = d.get("line") or ""
                findings.extend(self.scan_text(line, location="dialogue", scene_number=scene_num))

        return findings

    def audit_story(self, story: dict[str, Any]) -> list[VagueFinding]:
        """Audits an entire story structure for vague storytelling."""
        findings: list[VagueFinding] = []

        # Ending check
        ending = story.get("ending") or ""
        findings.extend(self.scan_text(ending, location="ending", scene_number=None))

        # Synopsis check
        synopsis = story.get("synopsis") or ""
        findings.extend(self.scan_text(synopsis, location="synopsis", scene_number=None))

        # Scenes check
        scenes = story.get("scenes") or []
        for sc in scenes:
            findings.extend(self.audit_scene(sc))

        return findings

    def calculate_vague_penalty(self, story: dict[str, Any]) -> tuple[int, list[str]]:
        """
        Calculates penalty points (0 to 30) deducted from story quality score.
        Returns (penalty_score, list of actionable critique messages).
        """
        findings = self.audit_story(story)
        if not findings:
            return 0, []

        # Each distinct vague instance costs 4 points up to max 30
        penalty = min(30, len(findings) * 4)
        critiques = [
            f"[Scene {f.scene_number or 'Ending'}] Found vague phrase '{f.phrase}' in {f.location}. "
            f"Context: {f.context}. Fix: Show the actual concrete event."
            for f in findings
        ]
        return penalty, critiques

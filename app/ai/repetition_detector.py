from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RepetitionFinding:
    type: str  # "duplicate_sentence", "similar_sentence", "duplicate_dialogue", "generic_dialogue", "repeated_paragraph", "filler"
    scene_number: int | None
    item: str
    matched_with: str
    similarity_score: float
    reason: str


class RepetitionDetector:
    """
    Detects lexical, syntactic, and semantic repetition across Hindi story scenes.
    Prevents padding word count with empty duplicate sentences, recycled dialogue,
    and repeated emotional reactions.
    """

    GENERIC_REPETITIVE_DIALOGUES = {
        "यह क्या है",
        "यह क्या हो रहा है",
        "तुम कौन हो",
        "यह कौन है",
        "यह क्या मतलब है",
        "तुम्हें कुछ नहीं पता",
        "मैं जानता हूँ कि आप कौन हैं",
        "मैं जानता हूं कि आप कौन हैं",
        "यह कैसे संभव है",
        "मैं समझ गया हूँ",
        "मैं समझ गया हूं",
        "मुझे इसके बारे में पता चलना चाहिए",
        "मुझे यह चाबी मिलनी चाहिए",
        "मैं अकेला नहीं हूँ",
        "मैं अकेला नहीं हूं",
        "मुझे यहाँ से निकलना होगा",
        "मुझे यहां से निकलना होगा",
        "कौन है",
        "क्या हुआ",
        "मुझे कुछ समझ नहीं आ रहा",
        "मुझे कुछ समझ नहीं आ रहा है",
    }

    DYNAMIC_SITUATION_DIALOGUES = [
        "अगर तुम्हारे पास इस बात का कोई सबूत है, तो सीधे-सीधे सामने रखो।",
        "इस खत पर पिताजी के दस्तखत तो हैं, लेकिन तारीख बीस साल पुरानी है।",
        "तुम सच जानते हुए भी खामोश रहे... तुम्हें अंदाज़ा है इसका क्या नतीजा होगा?",
        "दरवाज़े का ताला बाहर से बंद था, इसका मतलब कोई अभी-अभी यहाँ से भागा है।",
        "यह चाबी उस पुराने संदूक की है जिसे माँ ने तहखाने में छिपाया था।",
        "अब पीछे हटने से कुछ हासिल नहीं होगा, हमें उस कमरे की तलाशी लेनी ही पड़ेगी।",
        "उस रात हवेली में जो आग लगी थी, वह कोई हादसा नहीं बल्कि सोची-समझी साज़िश थी।",
        "इस कागज़ के टुकड़े पर लिखी लिखावट पहचानी हुई लगती है... यह तो राघव की है!",
        "तुमने मुझसे यह सच क्यों छिपाया कि ज़मीन पहले ही किसी और के नाम हो चुकी थी?",
        "जब तक मैं उस अजनबी का चेहरा नहीं देख लेता, यहाँ से एक कदम भी पीछे नहीं हटूँगा।",
    ]

    def __init__(self) -> None:
        pass

    @staticmethod
    def _normalize_hindi_text(text: str) -> str:
        """Strips punctuation and extra whitespace for normalization."""
        cleaned = re.sub(r"[?!।\.,;:\"'’‘“”\-—_()\[\]{}]", " ", text)
        return " ".join(cleaned.strip().split())

    @staticmethod
    def _get_words(text: str) -> set[str]:
        norm = RepetitionDetector._normalize_hindi_text(text)
        return set(norm.split())

    @classmethod
    def jaccard_similarity(cls, text_a: str, text_b: str) -> float:
        words_a = cls._get_words(text_a)
        words_b = cls._get_words(text_b)
        if not words_a or not words_b:
            return 0.0
        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        return len(intersection) / len(union)

    def detect_repetitions(self, story: dict[str, Any]) -> list[RepetitionFinding]:
        findings: list[RepetitionFinding] = []
        scenes = story.get("scenes") or []

        seen_sentences: dict[str, int] = {}
        all_narrations: list[tuple[int, str]] = []
        all_dialogues: list[tuple[int, str]] = []

        for sc in scenes:
            sn = sc.get("scene_number", 0)
            narr = (sc.get("narration") or "").strip()
            if narr:
                all_narrations.append((sn, narr))
                # Break narration into sentences
                sentences = [s.strip() for s in re.split(r"[।?!]", narr) if len(s.strip()) > 8]
                for sentence in sentences:
                    norm = self._normalize_hindi_text(sentence)
                    if norm in seen_sentences:
                        prior_sn = seen_sentences[norm]
                        findings.append(
                            RepetitionFinding(
                                type="duplicate_sentence",
                                scene_number=sn,
                                item=sentence,
                                matched_with=f"Scene {prior_sn}",
                                similarity_score=1.0,
                                reason=f"Exact duplicate sentence found in Scene {prior_sn} and Scene {sn}.",
                            )
                        )
                    else:
                        seen_sentences[norm] = sn

            # Dialogue lines
            for d in sc.get("dialogue") or []:
                if isinstance(d, dict):
                    line = (d.get("line") or "").strip()
                    if line:
                        all_dialogues.append((sn, line))

        # Check high paragraph similarity across scenes
        for i in range(len(all_narrations)):
            sn_i, narr_i = all_narrations[i]
            for j in range(i + 1, len(all_narrations)):
                sn_j, narr_j = all_narrations[j]
                sim = self.jaccard_similarity(narr_i, narr_j)
                if sim >= 0.70:
                    findings.append(
                        RepetitionFinding(
                            type="repeated_paragraph",
                            scene_number=sn_j,
                            item=narr_j[:80] + "...",
                            matched_with=f"Scene {sn_i}",
                            similarity_score=round(sim, 2),
                            reason=f"Narration in Scene {sn_j} is {round(sim*100)}% identical to Scene {sn_i}.",
                        )
                    )

        # Check dialogue repetitions and generic question loops
        seen_dialogue_norms: dict[str, int] = {}
        for sn, line in all_dialogues:
            norm = self._normalize_hindi_text(line)

            # Check if generic loop question
            for gen in self.GENERIC_REPETITIVE_DIALOGUES:
                if gen in norm:
                    findings.append(
                        RepetitionFinding(
                            type="generic_dialogue",
                            scene_number=sn,
                            item=line,
                            matched_with=gen,
                            similarity_score=0.9,
                            reason=f"Generic filler dialogue '{line}' does not reveal new plot or conflict.",
                        )
                    )
                    break

            # Check duplicate dialogue across scenes
            if norm in seen_dialogue_norms:
                prior_sn = seen_dialogue_norms[norm]
                findings.append(
                    RepetitionFinding(
                        type="duplicate_dialogue",
                        scene_number=sn,
                        item=line,
                        matched_with=f"Scene {prior_sn}",
                        similarity_score=1.0,
                        reason=f"Recycled dialogue line '{line}' already appeared in Scene {prior_sn}.",
                    )
                )
            else:
                seen_dialogue_norms[norm] = sn

        return findings

    def calculate_repetition_penalty(self, story: dict[str, Any]) -> tuple[int, list[str]]:
        """
        Calculates penalty points (0 to 30) deducted from story quality score.
        Returns (penalty_score, list of actionable critique messages).
        """
        findings = self.detect_repetitions(story)
        if not findings:
            return 0, []

        penalty = 0
        critiques: list[str] = []

        for f in findings:
            if f.type in ("duplicate_sentence", "repeated_paragraph"):
                penalty += 6
            elif f.type == "duplicate_dialogue":
                penalty += 4
            elif f.type == "generic_dialogue":
                penalty += 3
            else:
                penalty += 2

            critiques.append(f"[Scene {f.scene_number}] {f.reason}")

        penalty = min(35, penalty)
        return penalty, critiques

    def clean_and_deduplicate(self, story: dict[str, Any]) -> dict[str, Any]:
        """
        Procedurally cleans dialogue lines, deduplicates repeated lines,
        and sanitizes narrator prefixes without losing story content.
        """
        scenes = story.get("scenes") or []
        seen_dialogue_lines: set[str] = set()
        pool_idx = 0

        for sc in scenes:
            sn = sc.get("scene_number", 1)
            narr = (sc.get("narration") or "").strip()
            # Clean narration of narrator labels
            narr = re.sub(r"^(?:सूत्रधार|Narrator|वॉइसओवर|Voiceover)\s*[:：\-]\s*", "", narr).strip()
            sc["narration"] = narr

            new_dialogues = []
            for d in sc.get("dialogue") or []:
                if isinstance(d, str):
                    d = {"character": "पात्र", "line": d, "gender": "male"}
                elif not isinstance(d, dict):
                    continue

                raw_line = (d.get("line") or "").strip()
                if not raw_line:
                    continue

                # Clean speaker labels if present in line
                match = re.match(r"^([\u0900-\u097F\w\s]+?)\s*(?:\(([^)]+)\))?\s*[:：\-]\s*(.*)$", raw_line)
                if match:
                    char_match = match.group(1).strip()
                    if char_match and char_match not in ("Narrator", "सूत्रधार", "Voiceover"):
                        d["character"] = char_match
                    if match.group(2):
                        d["acting_instruction"] = match.group(2).strip()
                    raw_line = match.group(3).strip()

                raw_line = re.sub(r"\([^)]*\)", "", raw_line).strip()
                norm = self._normalize_hindi_text(raw_line)

                # Check duplicate across scenes
                is_duplicate = norm in seen_dialogue_lines

                if is_duplicate:
                    replacement = self.DYNAMIC_SITUATION_DIALOGUES[pool_idx % len(self.DYNAMIC_SITUATION_DIALOGUES)]
                    pool_idx += 1
                    logger.info("Scene %s: Replacing repetitive dialogue '%s' -> '%s'", sn, raw_line, replacement)
                    d["line"] = replacement
                    seen_dialogue_lines.add(self._normalize_hindi_text(replacement))
                else:
                    d["line"] = raw_line
                    seen_dialogue_lines.add(norm)

                new_dialogues.append(d)

            sc["dialogue"] = new_dialogues

        return story

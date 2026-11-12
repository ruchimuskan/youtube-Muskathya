from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings
from app.voice.segment_synthesizer import SegmentSynthesizer

HINDI_TEST_SENTENCES = [
    "रोहित की माँ ने कहा।",
    "रोहित की माँ ने कहा, यहाँ आओ।",
    "रोहित ने अपनी माँ से पूछा, आप कहाँ जा रही हैं?",
    "माँ ने प्यार से अपने बेटे को बुलाया।",
    "एक दिन रोहित जंगल में चला गया।",
    "अचानक उसके सामने एक अजीब आदमी आ गया।",
    "रोहित की माँ ने कहा, यहाँ आओ। रोहित ने पूछा, क्या हुआ माँ?",
    "एक दिन रोहित अपनी माँ के साथ बाजार गया। वहाँ उसने एक सुंदर खिलौना देखा।",
    "मुस्कान ने खिड़की से बाहर देखा और मुस्कुराई।",
    "आरव ने ईमानदारी से काम करना सीखा।",
    "गाँव के मेले में बहुत शोर था।",
    "बूढ़े किसान ने बच्चों को नैतिक सीख सुनाई।",
    "क्या तुम मेरी मदद करोगे?",
    "हाँ, मैं ज़रूर मदद करूँगा।",
    "महारानी ने राजा से अपनी चिंता व्यक्त की।",
    "अंधेरे कमरे में एक रहस्य छिपा था।",
    "सूरज निकलते ही पक्षी गाने लगे।",
    "बारिश की बूँदें पत्तों पर गिर रही थीं।",
    "दादी ने कहानी सुनाई और सब सो गए।",
    "छोटे बच्चे खेलते हुए खुश थे।",
    "वहाँ इसलिए गया क्योंकि माँ ने बुलाया था।",
    "यहाँ बैठो और शांति से सुनो।",
    "रोहित की माँ ने कहा, जल्दी करो, समय कम है।",
    "उसने सोचा, क्या यह सपना है?",
    "रास्ते पर एक अजनबी खड़ा था।",
    "मैं तुम्हें कभी नहीं भूलूँगा।",
    "उनकी दोस्ती हर मुश्किल में टूटी नहीं।",
    "रात ढलते ही तारे चमकने लगे।",
    "उसने ईमानदारी से माफी माँगी।",
    "आखिर में सभी खुशी से मिल बैठे।",
]


def run_voice_quality_report() -> dict:
    settings = get_settings()
    synth = SegmentSynthesizer()
    out_dir = settings.data_dir / "voice_quality"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    passed = 0
    for i, sentence in enumerate(HINDI_TEST_SENTENCES):
        wav = out_dir / f"sentence_{i:03d}.wav"
        try:
            _, prepared, recs = synth.synthesize_full(
                sentence,
                wav,
                verify=True,
                scene_number=i,
            )
            ok = all(r.get("verify_passed", True) for r in recs if r.get("segment_id") != "merged")
            if ok:
                passed += 1
            results.append(
                {
                    "index": i,
                    "sentence": sentence,
                    "segments": prepared.segments,
                    "audio": str(wav),
                    "passed": ok,
                }
            )
        except Exception as exc:
            results.append(
                {"index": i, "sentence": sentence, "passed": False, "error": str(exc)}
            )

    report = {
        "model": settings.piper_voice_hi_male,
        "total": len(HINDI_TEST_SENTENCES),
        "passed": passed,
        "results": results,
    }
    report_path = out_dir / "voice_quality_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

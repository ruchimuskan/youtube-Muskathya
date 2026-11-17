import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from app.ai.story_generator import StoryGenerator, StoryGenerationRequest

gen = StoryGenerator()
req = StoryGenerationRequest(
    language="hi",
    genre="horror_mystery",
    target_duration_sec=650,
    is_short=False,
    category_id="horror_mystery",
    min_scenes=18,
    max_scenes=22,
)
print("Starting story generation...")
story = gen.generate(req)
chars = gen._calculate_spoken_chars(story)
print(f"Generated title: {story.get('title')}")
print(f"Total scenes: {len(story.get('scenes', []))}")
print(f"Total spoken chars: {chars}")
print(f"Estimated duration: ~{chars / 12.5:.1f}s ({chars / 12.5 / 60:.1f}m)")

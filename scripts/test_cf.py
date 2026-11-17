import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import time
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from app.ai.providers.cloudflare import CloudflareWorkersAI

cf = CloudflareWorkersAI()
prompt = """Generate a 6-scene story JSON outline in Hindi for a mystery story.
Output JSON schema: {"title": "...", "scenes": [{"scene_number": 1, "narration": "...", "dialogue": []}]}"""

print("Sending request to Cloudflare...")
t0 = time.time()
try:
    resp = cf.complete(prompt, system="Output valid JSON only.", json_mode=True)
    print(f"Success in {time.time() - t0:.1f}s!")
    print("Response length:", len(resp.text))
    print("Preview:", resp.text[:300])
except Exception as e:
    print(f"Error after {time.time() - t0:.1f}s: {type(e).__name__}: {e}")

from __future__ import annotations


def zoompan_filter(size: str, duration_sec: float, fps: int, preset_index: int) -> str:
    """Ken Burns-style motion; preset_index rotates styles per scene."""
    d = max(int(duration_sec * fps), fps * 2)
    presets = [
        f"scale={size},zoompan=z='min(zoom+0.0008,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={size}:fps={fps}",
        f"scale={size},zoompan=z='if(lte(zoom,1.0),1.12,max(1.001,zoom-0.0008))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={size}:fps={fps}",
        f"scale={size},zoompan=z='1.08':x='if(lte(on,1),0,x+1)':y='ih/4':d={d}:s={size}:fps={fps}",
        f"scale={size},zoompan=z='1.08':x='if(lte(on,1),iw-ow,x-1)':y='ih/4':d={d}:s={size}:fps={fps}",
        f"scale={size},zoompan=z='1.06':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),0,y+0.5)':d={d}:s={size}:fps={fps}",
        f"scale={size},zoompan=z='min(zoom+0.0012,1.15)':x='iw/4':y='ih/2-(ih/zoom/2)':d={d}:s={size}:fps={fps}",
    ]
    return presets[preset_index % len(presets)]

from __future__ import annotations
import structlog
from pipeline.r2 import get_public_url, key_exists

log = structlog.get_logger(__name__)


def lookup_reference_clip(stroke_type: str, fault_label: str | None) -> str | None:
    """
    Returns the public CDN URL for a reference clip.
    Priority: fault-specific clip > canonical clip for stroke type > None.
    """
    # Fault-specific clip
    if fault_label:
        fault_key = f"clips/{stroke_type}/{fault_label}.mp4"
        if key_exists(fault_key):
            url = get_public_url(fault_key)
            log.info("reference_clip_found", key=fault_key, url=url)
            return url
        log.info("fault_clip_not_found_trying_canonical", fault_key=fault_key)

    # Canonical clip for stroke type
    canonical_key = f"clips/{stroke_type}/canonical.mp4"
    if key_exists(canonical_key):
        url = get_public_url(canonical_key)
        log.info("canonical_clip_found", key=canonical_key)
        return url

    log.warning("no_reference_clip_found", stroke_type=stroke_type, fault_label=fault_label)
    return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stroke", required=True)
    parser.add_argument("--fault")
    args = parser.parse_args()
    url = lookup_reference_clip(args.stroke, args.fault)
    print(f"Reference clip URL: {url}")

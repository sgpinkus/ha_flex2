"""Constants for flex2."""
import json
from pathlib import Path

DOMAIN = "flex2"

CONF_P_L = "p_l"
CONF_P_H = "p_h"
CONF_PRICE_ENTITY = "price_entity"

DEFAULT_P_L = -10.0
DEFAULT_P_H = -1.0

_manifest = json.loads((Path(__file__).parent / "manifest.json").read_text())
INTEGRATION_VERSION: str = _manifest.get("version", "0.0.0")
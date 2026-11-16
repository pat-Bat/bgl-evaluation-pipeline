from . import custom, must, vitaldb, berki, mimic3
from .base import EXTRACTORS


def get_extractor(config):
    extractor_type = config.get("type")

    if extractor_type not in EXTRACTORS:
        raise ValueError(
            f"Unknown extractor type: {extractor_type}. Available: {list(EXTRACTORS.keys())}"
        )

    extractor_class = EXTRACTORS[extractor_type]
    return extractor_class(config["config"])

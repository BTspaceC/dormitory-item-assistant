from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn


ROOT = Path(__file__).resolve().parents[1]


def test_model_metadata_matches_runtime_environment() -> None:
    metadata = json.loads((ROOT / "models" / "model_metadata.json").read_text(encoding="utf-8"))
    environment = metadata["environment"]

    assert environment["numpy"] == np.__version__
    assert environment["pandas"] == pd.__version__
    assert environment["scikit_learn"] == sklearn.__version__
    assert environment["joblib"] == joblib.__version__
    assert metadata["local_reviewed_holdout_rows"] == 10

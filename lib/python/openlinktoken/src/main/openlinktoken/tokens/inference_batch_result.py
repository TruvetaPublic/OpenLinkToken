# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field
from typing import List


@dataclass
class InferenceBatchResult:
    """Results of a batched inference pass.

    Attributes:
        signatures: Hex-encoded token signatures in the same order as the input rows.
    """

    signatures: List[str] = field(default_factory=list)

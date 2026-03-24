"""
Copyright (c) Truveta. All rights reserved.
"""

import math

from opentoken_core_ai.tokentransformer.rotation.rotation_quantizer import quantize


class TestRotationQuantizer:
    """Unit tests for the rotation quantizer."""

    def test_zero_maps_to_bin_100(self):
        """0.0 should map to bin 100 — the midpoint of [-5, 5] with width 0.05."""
        result = quantize([0.0])
        assert result == "100"

    def test_clamping_below_min_gives_bin_zero(self):
        """Values below min_val (-5.0) clamp to bin 0."""
        result = quantize([-100.0])
        assert result == "0"

    def test_clamping_above_max_gives_bin_199(self):
        """Values above max_val (+5.0) clamp to bin 199."""
        result = quantize([100.0])
        assert result == "199"

    def test_output_format_is_space_separated_integers(self):
        """Multiple values produce space-separated integer strings."""
        result = quantize([0.0, 1.0, -1.0])
        parts = result.split(" ")
        assert len(parts) == 3
        for part in parts:
            int(part)  # must be parseable as int — raises ValueError otherwise

    def test_min_val_maps_to_bin_zero(self):
        """Exactly min_val should map to bin 0."""
        result = quantize([-5.0])
        assert result == "0"

    def test_near_max_maps_to_bin_199(self):
        """A value just below max_val should map to bin 199 (last valid bin)."""
        # 4.999 is close to max: bin = floor((4.999 - (-5.0)) / 0.05) = floor(199.98) = 199
        result = quantize([4.999])
        assert result == "199"

    def test_num_bins_is_200(self):
        """num_bins = ceil(10.0 / 0.05) = 200, so valid range is [0, 199]."""
        num_bins = math.ceil(10.0 / 0.05)
        assert num_bins == 200

    def test_known_positive_value(self):
        """2.5 → bin = floor((2.5 - (-5.0)) / 0.05) = floor(150.0) = 150."""
        result = quantize([2.5])
        assert result == "150"

    def test_known_negative_value(self):
        """-2.5 → bin = floor((-2.5 - (-5.0)) / 0.05) = floor(50.0) = 50."""
        result = quantize([-2.5])
        assert result == "50"

    def test_empty_list_produces_empty_string(self):
        """Empty input list should produce an empty string."""
        result = quantize([])
        assert result == ""

    def test_single_value_produces_no_spaces(self):
        """A single-element list produces a string with no spaces."""
        result = quantize([0.0])
        assert " " not in result

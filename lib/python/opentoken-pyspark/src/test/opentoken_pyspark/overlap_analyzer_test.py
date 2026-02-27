"""
Copyright (c) Truveta. All rights reserved.

Tests for dataset overlap analyzer.
"""

import pytest
from pyspark.sql import SparkSession
from opentoken_pyspark.overlap_analyzer import OpenTokenOverlapAnalyzer
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter


@pytest.fixture(scope="module")
def spark():
    """Create a Spark session for testing."""
    return SparkSession.builder \
        .appName("OverlapAnalyzerTest") \
        .master("local[2]") \
        .getOrCreate()


@pytest.fixture
def encryption_key():
    """Standard 32-character encryption key for testing."""
    # Use exactly 32 ASCII characters
    return "12345678901234567890123456789012"


@pytest.fixture
def sample_tokens_df1(spark):
    """Create sample tokenized dataset 1."""
    data = [
        ("rec1", "T1", "token_a_t1"),
        ("rec1", "T2", "token_a_t2"),
        ("rec1", "T3", "token_a_t3"),
        ("rec2", "T1", "token_b_t1"),
        ("rec2", "T2", "token_b_t2"),
        ("rec2", "T3", "token_b_t3"),
        ("rec3", "T1", "token_c_t1"),
        ("rec3", "T2", "token_c_t2"),
        ("rec3", "T3", "token_c_t3"),
    ]
    return spark.createDataFrame(data, ["RecordId", "RuleId", "Token"])


@pytest.fixture
def sample_tokens_df2(spark):
    """Create sample tokenized dataset 2 with some overlap."""
    data = [
        ("rec10", "T1", "token_a_t1"),  # Matches rec1 from df1
        ("rec10", "T2", "token_a_t2"),
        ("rec10", "T3", "token_a_t3"),
        ("rec11", "T1", "token_b_t1"),  # Matches rec2 from df1
        ("rec11", "T2", "token_b_t2"),
        ("rec11", "T3", "token_b_t3"),
        ("rec12", "T1", "token_d_t1"),  # Unique to df2
        ("rec12", "T2", "token_d_t2"),
        ("rec12", "T3", "token_d_t3"),
    ]
    return spark.createDataFrame(data, ["RecordId", "RuleId", "Token"])


class TestOpenTokenOverlapAnalyzerInit:
    """Tests for OpenTokenOverlapAnalyzer initialization."""

    def test_init_valid_key(self, encryption_key):
        """Test initialization with valid encryption key."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        assert analyzer.encryption_key == encryption_key.encode('utf-8')

    def test_init_empty_key(self):
        """Test initialization with empty key raises ValueError."""
        with pytest.raises(ValueError, match="Encryption key cannot be empty"):
            OpenTokenOverlapAnalyzer("")

    def test_init_invalid_key_length(self):
        """Test initialization with wrong key length raises ValueError."""
        with pytest.raises(ValueError, match="must be exactly 32 bytes"):
            OpenTokenOverlapAnalyzer("short-key")


class TestAnalyzeOverlap:
    """Tests for overlap analysis functionality."""

    def test_analyze_overlap_single_rule(
        self, spark, encryption_key, sample_tokens_df1, sample_tokens_df2
    ):
        """Test overlap analysis with single matching rule."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        results = analyzer.analyze_overlap(
            sample_tokens_df1, sample_tokens_df2, ["T1"]
        )

        assert results['total_records_dataset1'] == 3
        assert results['total_records_dataset2'] == 3
        assert results['matching_records_dataset1'] == 2  # rec1, rec2
        assert results['matching_records_dataset2'] == 2  # rec10, rec11
        assert results['unique_to_dataset1'] == 1  # rec3
        assert results['unique_to_dataset2'] == 1  # rec12
        assert results['overlap_percentage'] > 0

    def test_analyze_overlap_multiple_rules(
        self, spark, encryption_key, sample_tokens_df1, sample_tokens_df2
    ):
        """Test overlap analysis requiring multiple matching rules."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        results = analyzer.analyze_overlap(
            sample_tokens_df1, sample_tokens_df2, ["T1", "T2", "T3"]
        )

        # Should match on all three rules
        assert results['matching_records_dataset1'] == 2  # rec1, rec2
        assert results['matching_records_dataset2'] == 2  # rec10, rec11

    def test_analyze_overlap_no_matches(self, spark, encryption_key):
        """Test overlap analysis with no matching records."""
        df1_data = [
            ("rec1", "T1", "token_a"),
            ("rec1", "T2", "token_b"),
        ]
        df2_data = [
            ("rec2", "T1", "token_c"),
            ("rec2", "T2", "token_d"),
        ]
        df1 = spark.createDataFrame(df1_data, ["RecordId", "RuleId", "Token"])
        df2 = spark.createDataFrame(df2_data, ["RecordId", "RuleId", "Token"])

        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        results = analyzer.analyze_overlap(df1, df2, ["T1"])

        assert results['matching_records_dataset1'] == 0
        assert results['matching_records_dataset2'] == 0
        assert results['overlap_percentage'] == 0

    def test_analyze_overlap_custom_dataset_names(
        self, encryption_key, sample_tokens_df1, sample_tokens_df2
    ):
        """Test overlap analysis with custom dataset names."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        results = analyzer.analyze_overlap(
            sample_tokens_df1,
            sample_tokens_df2,
            ["T1"],
            dataset1_name="Hospital_A",
            dataset2_name="Hospital_B"
        )

        assert results['dataset1_name'] == "Hospital_A"
        assert results['dataset2_name'] == "Hospital_B"
        assert "Hospital_A_RecordId" in results['matches'].columns
        assert "Hospital_B_RecordId" in results['matches'].columns

    def test_analyze_overlap_missing_columns(
        self, spark, encryption_key
    ):
        """Test that missing columns raise ValueError."""
        df_invalid = spark.createDataFrame(
            [("rec1", "token")],
            ["RecordId", "Token"]  # Missing RuleId
        )
        df_valid = spark.createDataFrame(
            [("rec1", "T1", "token")],
            ["RecordId", "RuleId", "Token"]
        )

        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        with pytest.raises(ValueError, match="must have columns"):
            analyzer.analyze_overlap(df_invalid, df_valid, ["T1"])

    def test_analyze_overlap_empty_rules(
        self, encryption_key, sample_tokens_df1, sample_tokens_df2
    ):
        """Test that empty matching rules raise ValueError."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        with pytest.raises(ValueError, match="matching_rules cannot be empty"):
            analyzer.analyze_overlap(
                sample_tokens_df1, sample_tokens_df2, []
            )

    def test_analyze_overlap_matches_dataframe(
        self, encryption_key, sample_tokens_df1, sample_tokens_df2
    ):
        """Test that matches DataFrame is returned correctly."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        results = analyzer.analyze_overlap(
            sample_tokens_df1, sample_tokens_df2, ["T1"]
        )

        matches_df = results['matches']
        assert matches_df.count() == 2  # rec1-rec10, rec2-rec11
        assert "Dataset1_RecordId" in matches_df.columns
        assert "Dataset2_RecordId" in matches_df.columns

    def test_decrypt_token_legacy_format(self, encryption_key):
        """Legacy encrypted tokens decrypt to deterministic values."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        plaintext = "deterministic-hash-value"
        encrypted = EncryptTokenTransformer(encryption_key).transform(plaintext)

        assert analyzer._decrypt_token(encrypted) == plaintext

    def test_decrypt_token_v1_format(self, encryption_key):
        """ot.V1 tokens decrypt to deterministic values for matching."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        plaintext = "deterministic-hash-value"
        legacy_encrypted = EncryptTokenTransformer(encryption_key).transform(plaintext)
        v1_encrypted = JweMatchTokenFormatter(
            encryption_key=encryption_key,
            ring_id="ring-test",
            rule_id="T1"
        ).transform(legacy_encrypted)

        assert v1_encrypted.startswith("ot.V1.")
        assert analyzer._decrypt_token(v1_encrypted) == plaintext


class TestCompareWithMultipleRules:
    """Tests for comparing with multiple rule sets."""

    def test_compare_with_multiple_rules(
        self, encryption_key, sample_tokens_df1, sample_tokens_df2
    ):
        """Test comparison with multiple rule sets."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        rule_sets = [["T1"], ["T1", "T2"], ["T1", "T2", "T3"]]
        results = analyzer.compare_with_multiple_rules(
            sample_tokens_df1, sample_tokens_df2, rule_sets
        )

        assert len(results) == 3
        for result in results:
            assert 'overlap_percentage' in result
            assert 'matching_records_dataset1' in result

    def test_compare_different_overlap_rates(
        self, spark, encryption_key
    ):
        """Test that different rules produce different overlap rates."""
        # Create datasets where T1 matches but T2 doesn't for some records
        df1_data = [
            ("rec1", "T1", "token_a"),
            ("rec1", "T2", "token_b"),
            ("rec2", "T1", "token_c"),
            ("rec2", "T2", "token_d"),
        ]
        df2_data = [
            ("rec10", "T1", "token_a"),  # T1 matches
            ("rec10", "T2", "token_x"),  # T2 doesn't match
            ("rec11", "T1", "token_c"),  # T1 matches
            ("rec11", "T2", "token_d"),  # T2 matches
        ]
        df1 = spark.createDataFrame(df1_data, ["RecordId", "RuleId", "Token"])
        df2 = spark.createDataFrame(df2_data, ["RecordId", "RuleId", "Token"])

        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        rule_sets = [["T1"], ["T1", "T2"]]
        results = analyzer.compare_with_multiple_rules(df1, df2, rule_sets)

        # T1 only should match both records
        assert results[0]['matching_records_dataset1'] == 2
        # T1+T2 should match only one record
        assert results[1]['matching_records_dataset1'] == 1


class TestPrintSummary:
    """Tests for summary printing functionality."""

    def test_print_summary_no_error(
        self, encryption_key, sample_tokens_df1, sample_tokens_df2, capsys
    ):
        """Test that print_summary executes without error."""
        analyzer = OpenTokenOverlapAnalyzer(encryption_key)
        results = analyzer.analyze_overlap(
            sample_tokens_df1, sample_tokens_df2, ["T1"]
        )

        # Should not raise any exceptions
        analyzer.print_summary(results)

        # Verify output contains expected elements
        captured = capsys.readouterr()
        assert "Dataset Overlap Analysis" in captured.out
        assert "Total records:" in captured.out
        assert "Matching records:" in captured.out
        assert "Overlap Percentage:" in captured.out

"""
Copyright (c) Truveta. All rights reserved.

Tests for the TokenDecryptionProcessor class.
"""

from unittest.mock import Mock, patch

from opentoken_cli.processor.token_decryption_processor import TokenDecryptionProcessor
from opentoken_cli.processor.token_constants import TokenConstants
from opentoken.tokens.token import Token
from opentoken.tokentransformer.decrypt_token_transformer import DecryptTokenTransformer
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter


class TestTokenDecryptionProcessor:
    """Unit tests for TokenDecryptionProcessor."""

    ENCRYPTION_KEY = "12345678901234567890123456789012"
    RING_ID = "ring-1"

    def test_process_decrypts_tokens(self):
        """Test that tokens are correctly decrypted."""
        # Setup mock reader with test data
        row1 = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T1",
            TokenConstants.TOKEN: "encryptedToken1"
        }
        row2 = {
            TokenConstants.RECORD_ID: "record-2",
            TokenConstants.RULE_ID: "T2",
            TokenConstants.TOKEN: "encryptedToken2"
        }
        
        mock_reader = iter([row1, row2])
        mock_writer = Mock()
        mock_decryptor = Mock()
        mock_decryptor.transform.side_effect = ["decryptedToken1", "decryptedToken2"]

        # Execute
        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
        )

        # Verify
        assert mock_writer.write_token.call_count == 2
        # Check that decrypted tokens were written
        calls = mock_writer.write_token.call_args_list
        assert calls[0][0][0][TokenConstants.TOKEN] == "decryptedToken1"
        assert calls[1][0][0][TokenConstants.TOKEN] == "decryptedToken2"

    def test_process_skips_blank_tokens(self):
        """Test that BLANK tokens are not decrypted."""
        row = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T1",
            TokenConstants.TOKEN: Token.BLANK
        }
        
        mock_reader = iter([row])
        mock_writer = Mock()
        mock_decryptor = Mock()

        # Execute
        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
        )

        # Verify decryptor was not called for blank token
        mock_decryptor.transform.assert_not_called()
        # Verify token was still written
        mock_writer.write_token.assert_called_once_with(row)

    def test_process_skips_empty_tokens(self):
        """Test that empty tokens are not decrypted."""
        row = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T1",
            TokenConstants.TOKEN: ""
        }
        
        mock_reader = iter([row])
        mock_writer = Mock()
        mock_decryptor = Mock()

        # Execute
        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
        )

        # Verify decryptor was not called for empty token
        mock_decryptor.transform.assert_not_called()
        mock_writer.write_token.assert_called_once()

    def test_process_handles_decryption_error(self):
        """Test that decryption errors are logged and original token is kept."""
        row = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T1",
            TokenConstants.TOKEN: "invalidEncryptedToken"
        }
        
        mock_reader = iter([row])
        mock_writer = Mock()
        mock_decryptor = Mock()
        mock_decryptor.transform.side_effect = Exception("Decryption failed")

        # Execute - should not throw
        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
        )

        # Verify token was still written with original encrypted value
        mock_writer.write_token.assert_called_once()
        written_row = mock_writer.write_token.call_args[0][0]
        assert written_row[TokenConstants.TOKEN] == "invalidEncryptedToken"

    def test_process_multiple_tokens_with_mixed_content(self):
        """Test processing multiple tokens including blank and valid ones."""
        row1 = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T1",
            TokenConstants.TOKEN: "encryptedToken1"
        }
        row2 = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T2",
            TokenConstants.TOKEN: Token.BLANK
        }
        row3 = {
            TokenConstants.RECORD_ID: "record-2",
            TokenConstants.RULE_ID: "T1",
            TokenConstants.TOKEN: "encryptedToken3"
        }
        
        mock_reader = iter([row1, row2, row3])
        mock_writer = Mock()
        mock_decryptor = Mock()
        mock_decryptor.transform.side_effect = ["decryptedToken1", "decryptedToken3"]

        # Execute
        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
        )

        # Verify all tokens were written
        assert mock_writer.write_token.call_count == 3
        # Verify decryptor was only called for non-blank tokens
        assert mock_decryptor.transform.call_count == 2

    def test_process_empty_input(self):
        """Test processing empty input."""
        mock_reader = iter([])
        mock_writer = Mock()
        mock_decryptor = Mock()

        # Execute
        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
        )

        # Verify no tokens were written
        mock_writer.write_token.assert_not_called()

    def test_process_logs_progress_every_10000_rows(self):
        """Test that progress is logged every 10000 rows."""
        # Create 10001 rows to trigger one progress log
        rows = [
            {
                TokenConstants.RECORD_ID: f"record-{i}",
                TokenConstants.RULE_ID: "T1",
                TokenConstants.TOKEN: f"token{i}"
            }
            for i in range(10001)
        ]
        
        mock_reader = iter(rows)
        mock_writer = Mock()
        mock_decryptor = Mock()
        mock_decryptor.transform.return_value = "decrypted"

        with patch('opentoken_cli.processor.token_decryption_processor.logger') as mock_logger:
            # Execute
            TokenDecryptionProcessor.process_with_key(
                mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
            )

            # Verify info was logged (progress + summary)
            info_calls = [call for call in mock_logger.info.call_args_list]
            # Should have at least one progress log and final summary logs
            assert len(info_calls) >= 3  # 10000 progress + "total" + "decrypted" logs

    def test_process_handles_missing_token_key(self):
        """Test handling of row with missing Token key."""
        row = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T1"
            # No Token key
        }
        
        mock_reader = iter([row])
        mock_writer = Mock()
        mock_decryptor = Mock()

        # Execute - should not throw
        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, mock_decryptor, self.ENCRYPTION_KEY
        )

    def test_process_decrypts_jwe_tokens(self):
        """Test that JWE tokens are decrypted and unwrapped correctly."""
        plain_token = "plain-token"
        encryptor = EncryptTokenTransformer(self.ENCRYPTION_KEY)
        decryptor = DecryptTokenTransformer(self.ENCRYPTION_KEY)
        formatter = JweMatchTokenFormatter(self.ENCRYPTION_KEY, self.RING_ID, "T1")

        encrypted_token = encryptor.transform(plain_token)
        jwe_token = formatter.transform(encrypted_token)

        row = {
            TokenConstants.RECORD_ID: "record-1",
            TokenConstants.RULE_ID: "T1",
            TokenConstants.TOKEN: jwe_token
        }

        mock_reader = iter([row])
        mock_writer = Mock()

        TokenDecryptionProcessor.process_with_key(
            mock_reader, mock_writer, decryptor, self.ENCRYPTION_KEY
        )

        written_row = mock_writer.write_token.call_args[0][0]
        assert written_row[TokenConstants.TOKEN] == plain_token

        mock_writer.write_token.assert_called_once()

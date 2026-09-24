from openlinktoken.tokens.inference_signature_provider import InferenceBatchResult


def test_inference_batch_result_is_defined_in_dedicated_module():
    """
    Verify that inference batch result is defined in dedicated module.
    """
    assert InferenceBatchResult.__module__ == "openlinktoken.tokens.inference_batch_result"

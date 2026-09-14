from openlinktoken.tokens.inference_signature_provider import InferenceBatchResult


def test_inference_batch_result_is_defined_in_dedicated_module():
    assert InferenceBatchResult.__module__ == "openlinktoken.tokens.inference_batch_result"

from app.core.security import generate_access_token, verify_access_token


def test_generate_access_token():
    """Test that generate_access_token returns valid token, prefix, and hash."""
    token, prefix, token_hash = generate_access_token()

    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # Prefix should be first 8 characters of token
    assert prefix == token[:8]
    assert len(prefix) == 8

    # Hash should be different from token
    assert token_hash != token
    assert len(token_hash) > 0


def test_verify_access_token():
    """Test that verify_access_token correctly validates tokens."""
    token, prefix, token_hash = generate_access_token()

    # Correct token should verify
    assert verify_access_token(token, token_hash) is True

    # Wrong token should not verify
    assert verify_access_token("wrong_token", token_hash) is False

    # Wrong hash should not verify
    wrong_token, _, wrong_hash = generate_access_token()
    assert verify_access_token(token, wrong_hash) is False


def test_tokens_are_unique():
    """Test that each generated token is unique."""
    token1, prefix1, hash1 = generate_access_token()
    token2, prefix2, hash2 = generate_access_token()

    # Tokens should be different
    assert token1 != token2
    assert prefix1 != prefix2
    assert hash1 != hash2

from auth.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hashing_does_not_store_plaintext() -> None:
    password = "ChangeMe123!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("WrongPassword123!", hashed_password)


def test_access_token_round_trip() -> None:
    token = create_access_token(subject="user-123", claims={"tenant_id": "tenant-123", "role": "ADMIN"})

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-123"
    assert payload["role"] == "ADMIN"

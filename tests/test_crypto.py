from app.crypto_algorithms import (
    NonReversibleAlgorithmError,
    aes_decrypt,
    aes_encrypt,
    caesar_decrypt,
    caesar_encrypt,
    md5_hash,
    process_text,
    rail_fence_decrypt,
    rail_fence_encrypt,
    sha256_hash,
)


def test_caesar_roundtrip():
    plain = "Hello, World!"
    encrypted = caesar_encrypt(plain, 3)
    assert encrypted == "Khoor, Zruog!"
    assert caesar_decrypt(encrypted, 3) == plain


def test_rail_fence_roundtrip():
    plain = "WEAREDISCOVEREDFLEEATONCE"
    encrypted = rail_fence_encrypt(plain, 3)
    assert encrypted == "WECRLTEERDSOEEFEAOCAIVDEN"
    assert rail_fence_decrypt(encrypted, 3) == plain


def test_hash_outputs():
    assert md5_hash("abc") == "900150983cd24fb0d6963f7d28e17f72"
    assert (
        sha256_hash("abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_non_reversible_hash_decrypt():
    try:
        process_text("MD5", "decrypt", "abc", "")
        assert False, "expected NonReversibleAlgorithmError"
    except NonReversibleAlgorithmError:
        assert True


def test_aes_roundtrip():
    plain = "Offline encryption text"
    token = aes_encrypt(plain, "strong-passphrase")
    assert token
    assert aes_decrypt(token, "strong-passphrase") == plain

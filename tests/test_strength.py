from app.strength import evaluate_password


def test_weak_password_scoring():
    result = evaluate_password("123456")
    assert result.score < 40
    assert result.level == "弱"
    assert result.flags["is_common"] is True


def test_strong_password_scoring():
    result = evaluate_password("N3xT!Wave#2026")
    assert result.score >= 80
    assert result.level in {"强", "极强"}
    assert result.flags["is_common"] is False


def test_repeated_pattern_detected():
    result = evaluate_password("Ab12Ab12Ab12")
    assert result.flags["has_repeat_pattern"] is True

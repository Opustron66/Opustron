from chronicle.guard.pseudonymizer import pseudonymize


def test_email_is_redacted():
    assert pseudonymize("Contact a@example.com") == "Contact [EMAIL]"

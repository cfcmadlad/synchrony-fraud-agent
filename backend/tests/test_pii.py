from agent.pii import scrub_pii, scrub_record


def test_ssn_is_redacted():
    assert scrub_pii("ssn 123-45-6789 on file") == "ssn [SSN_REDACTED] on file"


def test_email_is_redacted():
    assert scrub_pii("contact test@example.com now") == "contact [EMAIL_REDACTED] now"


def test_phone_is_redacted():
    assert scrub_pii("call 555-123-4567 today") == "call [PHONE_REDACTED] today"


def test_card_number_is_redacted():
    result = scrub_pii("card 4111 1111 1111 1111 was used")
    assert "[CARD_NUMBER_REDACTED]" in result
    assert "4111" not in result


def test_paysim_style_account_ids_are_left_untouched():
    assert scrub_pii("account C1231006815 balance 5000.00") == "account C1231006815 balance 5000.00"
    assert scrub_pii("M1979787155 destination account") == "M1979787155 destination account"


def test_scrub_record_only_touches_account_fields():
    record = {
        "origin_account": "test@example.com",
        "dest_account": "C123",
        "amount": 100.0,
        "event_type": "loan_disbursement",
    }
    scrubbed = scrub_record(record)
    assert scrubbed["origin_account"] == "[EMAIL_REDACTED]"
    assert scrubbed["dest_account"] == "C123"
    assert scrubbed["amount"] == 100.0


def test_scrub_record_handles_none_dest_account():
    record = {"origin_account": "C1", "dest_account": None}
    scrubbed = scrub_record(record)
    assert scrubbed["dest_account"] is None

import pandas as pd

from ml.features import FEATURE_COLUMNS, build_features, build_features_single


def make_record(**overrides):
    record = {
        "event_type": "loan_disbursement",
        "step": 5,
        "amount": 5000.0,
        "origin_account": "C1",
        "dest_account": "M1",
        "origin_balance_before": 5000.0,
        "origin_balance_after": 0.0,
        "dest_balance_before": 1000.0,
        "dest_balance_after": 6000.0,
    }
    record.update(overrides)
    return record


def test_feature_columns_match_output_columns():
    result = build_features_single(make_record())
    assert list(result.columns) == FEATURE_COLUMNS


def test_fully_drained_disbursement_flagged():
    result = build_features_single(make_record()).iloc[0]
    assert result["origin_balance_after_zero"] == 1
    assert result["origin_balance_delta"] == -5000.0


def test_event_type_one_hot_is_exclusive():
    result = build_features_single(make_record(event_type="fee_charge")).iloc[0]
    assert result["event_type_fee_charge"] == 1
    assert result["event_type_loan_disbursement"] == 0


def test_missing_optional_fields_default_to_zero():
    record = make_record(
        step=None,
        origin_balance_before=None,
        origin_balance_after=None,
        dest_balance_before=None,
        dest_balance_after=None,
    )
    result = build_features_single(record).iloc[0]
    assert result["origin_balance_before"] == 0.0
    assert result["hour_of_day"] == 0


def test_amount_to_balance_ratio_avoids_division_by_zero():
    record = make_record(origin_balance_before=0.0, amount=100.0)
    result = build_features_single(record).iloc[0]
    assert result["amount_to_origin_balance_ratio"] == 100.0


def test_build_features_batches_multiple_rows():
    df = pd.DataFrame([make_record(), make_record(event_type="installment_repayment")])
    result = build_features(df)
    assert len(result) == 2
    assert list(result.columns) == FEATURE_COLUMNS

SUPERVISED_HIGH = 0.5
ANOMALY_HIGH = 0.5
DRAIN_RATIO_THRESHOLD = 0.9
TOKEN_PAYMENT_RATIO_THRESHOLD = 0.02

SYNTHETIC_IDENTITY_ORIGINATION = "synthetic_identity_origination"
PROMOTIONAL_FINANCING_ABUSE = "promotional_financing_abuse"
ACCOUNT_TAKEOVER_PATTERN = "account_takeover_pattern"
ELEVATED_RISK_UNCLASSIFIED = "elevated_risk_unclassified"
NORMAL_ACTIVITY = "normal_activity"

ARCHETYPE_LABELS = {
    SYNTHETIC_IDENTITY_ORIGINATION: "Synthetic identity at loan origination",
    PROMOTIONAL_FINANCING_ABUSE: "Promotional financing abuse",
    ACCOUNT_TAKEOVER_PATTERN: "Account takeover on servicing app",
    ELEVATED_RISK_UNCLASSIFIED: "Elevated risk, unclassified pattern",
    NORMAL_ACTIVITY: "Normal activity",
}


def tag_archetype(record: dict, scores: dict) -> dict:
    event_type = record.get("event_type")
    amount = record.get("amount") or 0.0
    origin_before = record.get("origin_balance_before") or 0.0
    origin_after = record.get("origin_balance_after") or 0.0

    supervised_score = scores["supervised_score"]
    anomaly_score = scores["anomaly_score"]
    risk_score = scores["risk_score"]

    ratio = amount / (origin_before + 1.0)
    fully_drained = origin_before > 0.0 and origin_after == 0.0

    if event_type == "loan_disbursement" and supervised_score >= SUPERVISED_HIGH and fully_drained:
        return {
            "archetype": SYNTHETIC_IDENTITY_ORIGINATION,
            "label": ARCHETYPE_LABELS[SYNTHETIC_IDENTITY_ORIGINATION],
            "rationale": (
                f"Loan disbursement of {amount:.2f} was followed by the origin account "
                f"balance dropping from {origin_before:.2f} to zero, matching the "
                "learned pattern of accounts opened to be drained immediately."
            ),
        }

    if (
        event_type == "installment_repayment"
        and anomaly_score >= ANOMALY_HIGH
        and 0 < ratio <= TOKEN_PAYMENT_RATIO_THRESHOLD
    ):
        return {
            "archetype": PROMOTIONAL_FINANCING_ABUSE,
            "label": ARCHETYPE_LABELS[PROMOTIONAL_FINANCING_ABUSE],
            "rationale": (
                f"Installment repayment of {amount:.2f} is only {ratio:.4f} of the "
                "outstanding origin balance, an anomalously small token payment relative "
                "to this account's history."
            ),
        }

    if (
        event_type in ("fee_charge", "account_funding")
        and anomaly_score >= ANOMALY_HIGH
        and ratio >= DRAIN_RATIO_THRESHOLD
    ):
        return {
            "archetype": ACCOUNT_TAKEOVER_PATTERN,
            "label": ARCHETYPE_LABELS[ACCOUNT_TAKEOVER_PATTERN],
            "rationale": (
                f"A {event_type.replace('_', ' ')} of {amount:.2f} moved "
                f"{ratio:.2%} of the account's balance in a single event, an anomalous "
                "spike inconsistent with this event type's normal behavior."
            ),
        }

    if risk_score >= SUPERVISED_HIGH:
        return {
            "archetype": ELEVATED_RISK_UNCLASSIFIED,
            "label": ARCHETYPE_LABELS[ELEVATED_RISK_UNCLASSIFIED],
            "rationale": (
                f"Fused risk score of {risk_score:.2f} is elevated but does not match "
                "any known archetype pattern."
            ),
        }

    return {
        "archetype": NORMAL_ACTIVITY,
        "label": ARCHETYPE_LABELS[NORMAL_ACTIVITY],
        "rationale": f"Fused risk score of {risk_score:.2f} is within normal range.",
    }

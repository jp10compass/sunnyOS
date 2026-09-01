# -*- coding: utf-8 -*-
"""SOS P&L Draft - Streamlit App

FVRC P&L DETAIL CLEANING AND PROPERTY / BOOKING MAPPING

Converted from a Google Colab notebook to run as a Streamlit app.

Upload three files in the app:

1. Original FVRC Profit and Loss Detail CSV
2. Additional one-column property-list CSV
3. Booking-to-property CSV with:
      Lease ID
      Unit Name
"""

import os
import re
import unicodedata
from collections import defaultdict

import pandas as pd
import streamlit as st


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    """
    Clean text while preserving capitalization.

    - Converts missing values to blank
    - Normalizes Unicode characters
    - Replaces non-breaking spaces
    - Removes leading and trailing spaces
    - Replaces repeated spaces with one space
    """

    if pd.isna(value):
        return ""

    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_text(value):
    """
    Normalize text for comparisons.

    Comparisons ignore:
    - Capitalization
    - Leading and trailing spaces
    - Repeated spaces
    """

    return clean_text(value).casefold()


def normalize_account_name(value):
    """
    Normalize Account Name values.

    Also ignores spaces immediately before or after colons.
    """

    text = normalize_text(value)
    text = re.sub(r"\s*:\s*", ":", text)

    return text


def parse_amount(value):
    """
    Parse a currency-formatted Amount value into a float.

    Handles a leading "$", thousands-separator commas, and both
    "-123.45" and parenthesized "(123.45)" negative formats.

    Returns None if the value is blank or cannot be parsed.
    """

    text = clean_text(value)

    if text == "":
        return None

    negative = (
        text.startswith("-")
        or (text.startswith("(") and text.endswith(")"))
    )

    text = text.strip("()")
    text = text.replace("$", "").replace(",", "").replace("-", "")

    try:
        amount = float(text)
    except ValueError:
        return None

    return -amount if negative else amount


def normalize_booking_id(value):
    """
    Normalize booking IDs for matching.

    - Converts to uppercase
    - Removes spaces
    - Standardizes different dash characters
    """

    text = clean_text(value).upper()

    text = (
        text
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    text = re.sub(r"\s+", "", text)

    return text


def read_csv_without_header(uploaded_file, skip_blank_lines=False):
    """
    Read a CSV without assigning a header row.
    All values are imported as text.
    """

    uploaded_file.seek(0)

    try:
        return pd.read_csv(
            uploaded_file,
            header=None,
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=skip_blank_lines,
            encoding="utf-8-sig"
        )

    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(
            uploaded_file,
            header=None,
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=skip_blank_lines,
            encoding="latin-1"
        )


def read_csv_with_header(uploaded_file):
    """
    Read a CSV whose first row contains headers.
    All values are imported as text.
    """

    uploaded_file.seek(0)

    try:
        return pd.read_csv(
            uploaded_file,
            header=0,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig"
        )

    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(
            uploaded_file,
            header=0,
            dtype=str,
            keep_default_na=False,
            encoding="latin-1"
        )


def find_column(dataframe, expected_column_name):
    """
    Find a column while ignoring capitalization and extra spaces.
    """

    expected_normalized = normalize_text(expected_column_name)

    for column in dataframe.columns:

        if normalize_text(column) == expected_normalized:
            return column

    available_columns = [
        str(column)
        for column in dataframe.columns
    ]

    raise KeyError(
        f'The column "{expected_column_name}" was not found.\n'
        f"Available columns: {available_columns}"
    )


# ============================================================
# BASE VALID-PROPERTY LIST
#
# FVRC, BRI, and blank values are intentionally excluded.
# ============================================================

BASE_PROPERTIES_TEXT = """
1012 Mandalay
1015 Eldorado
1021 Mandalay
10265 115th Ave N
1039 Union
10738 126th Ave
1122 Charles
1289 Pierce 1
1289 Pierce 2
1289 Pierce 3
1289 Pierce 4
1565 S Jefferson
1612 Lakeview
16333 Gulf Blvd 215
18 Heilwood 1
18 Heilwood 2
180 Devon
19622 Gulf
20 Kendall 1
20 Kendall 2
2008 20th Ave Parkway
2009 Edgewater
2025 Scotland Dr
22 Laurel
2200 Spanish Vista N
2200 Spanish Vista S
2201 Spanish Vista N
2201 Spanish Vista S
26 Heilwood
2760 Gulf 2
435 18th Avenue
620 Bayway Unit 1
676 Mandalay 111
729 Bruce
729 Mandalay
733 Bay Esplanade
739 Eldorado
755 Bruce
760 Bay Esplanade
764 Mandalay Ave 2
764 Mandalay Ave 2br
770 Bay Esplanade
770 Bay Unit 2
770 Mandalay
800 Lantana
806 Lantana
823 Eldorado Ave
8500 Ulmerton 212
865 Lantana
870 1/2 Bruce
870 Bay Esplanade
870 Bruce
917 Mandalay
929 Bruce
930 Mandalay
934 Narcissus
939 Narcissus
944 Eldorado
971 Eldorado
980 Narcissus
BH 403
BH 71
BW 1
BW 2
BW 3
BW 6
CBS 102
CBS 103
CBS 104
CBS 105
CBS 106
CBS 107
CBS 201
CBS 202
CBS 203
CBS 204
CBS 205
CBS 206
CR A1
CR A4
CR B1
CR B2
CR B5
CR C2
CR D1
CR E2
SK 601
TT 10
TT 11
TT 12
TT 15
TT 16
TT 18
TT 19
TT 21
TT 22
TT 23
TT 24
TT 26
TT 27
TT 29
TT 3
TT 31
TT 32
TT 35
TT 37
TT 38
TT 39
TT 4
TT 40
TT 41
TT 44
TT 45
TT 48
TT 49
TT 50
TT 51
TT 54
TT 55
TT 56
TT 59
TT 8
TT 9
TT HOA
"""

BASE_PROPERTIES = [
    clean_text(property_name)
    for property_name
    in BASE_PROPERTIES_TEXT.strip().splitlines()
    if clean_text(property_name) != ""
]


# ============================================================
# CORPORATE ACCOUNT LIST
#
# Corporate tagging runs before all other mapping.
#
# For these accounts:
#
# Property = Corporate
# Booking  = Corporate
# ============================================================

CORPORATE_ACCOUNT_NAMES = [
    "Accounting Fees",
    "Bank Service Charges",
    "Interest Expense",
    "Licenses",
    "Office Supplies",
    "Payroll Costs",
    "Payroll Costs:Employee Benefits",
    "Payroll Costs:Payroll Fees",
    "Payroll Costs:Payroll Guest Services",
    "Payroll Costs:Payroll Taxes",
    "Payroll Costs:Subcontractor Guest Services",
    "Rent",
    "Software",
    "Telephone:Phone",
    "Uncategorized Expense",
    "Reconciliation Discrepancies",
    "Tax Collection Allowance"
]


# ============================================================
# STEP 2: ACCOUNT SPLIT RULES
#
# Some accounts mix income and cost in a single account. Each
# rule below assigns matching rows a "Classification" of either
# the rule's income_label or cost_label (or blank, if excluded /
# flagged for review) and records a sign-corrected value in
# "Adjusted Amount".
#
# Nothing is overwritten in place — "Account", "Transaction
# Type", "Name", "Amount", "Description", and every other
# original column always keep their original values.
# "Classification" and "Adjusted Amount" are the two new columns
# added by Step 2.
#
# The account is matched by comparing the normalized "Account
# Name" field (blank-safe, trimmed, case-insensitive — see
# normalize_account_name()) against "source_account" exactly.
#
# rule_type == "name_based":
#   Classification comes from the "Name" column.
#   - Name matches one of "cost_name_values"  -> Cost
#   - Name is nonblank and does not match      -> Income
#   - Name is blank                            -> the user is
#     asked to tag the row as Income or Cost
#
# rule_type == "transaction_type_based":
#   Classification comes from the single centralized
#   classify_by_transaction_type() function below, driven by
#   one of two mappings on the rule (never both):
#   - "transaction_type_map" (and, optionally, "sign_based_types"
#     for accounts where a specific Transaction Type is decided
#     by the Amount sign instead of a fixed lookup — see
#     Housekeeping Clearing). Amount sign is NOT used unless a
#     type is explicitly listed in "sign_based_types".
#   - "transaction_type_sign_map", for accounts where the sign of
#     the Amount matters PER Transaction Type rather than as a
#     fixed lookup or a uniform sign rule — e.g. {"bill":
#     {"positive": "Cost", "zero": "Cost"}} maps a positive or
#     zero Bill to Cost and leaves a negative Bill unclassified
#     (see the Maintenance accounts). Any Transaction Type, or
#     any sign of a listed Transaction Type, missing from the map
#     is left unclassified and flagged for review.
#   Either way, Transaction Types (or signs) not covered by the
#   rule are left unclassified and flagged for review — nothing
#   is asked of the user.
#
# To add another account: add a new rule entry (and, for
# transaction_type_based rules, a new *_TRANSACTION_TYPE_MAP or
# *_TRANSACTION_TYPE_SIGN_MAP dict below). Do not write a new
# classification function.
# ============================================================

HOUSEKEEPING_TRANSACTION_TYPE_MAP = {
    "bill": "Cost",
    "credit memo": "Income",
    "deposit": "Cost",
    "refund": "Income",
    "revenue recognition": "Income",
    "vendor credit": "Income",
}

# OTA / booking-channel commission account. Unrelated to
# property-management commissions — those are not covered by
# this rule.
OTA_COMMISSION_TRANSACTION_TYPE_MAP = {
    "revenue recognition": "Income",
    "refund": "Income",
    "credit memo": "Income",
    "expense": "Cost",
    "bill": "Cost",
}

HOA_TRANSACTION_TYPE_MAP = {
    "bill": "Cost",
    "credit memo": "Income",
    "refund": "Income",
    "revenue recognition": "Income",
    "vendor credit": "Income",
}

TRAVEL_INSURANCE_TRANSACTION_TYPE_MAP = {
    "bill": "Cost",
    "refund": "Income",
    "revenue recognition": "Income",
}

CAM_TRANSACTION_TYPE_MAP = {
    "credit memo": "Income",
    "refund": "Income",
    "revenue recognition": "Income",
    "expense": "Cost",
}

# Bill -> Income and Vendor Credit -> Income are PROVISIONAL,
# pending bookkeeper confirmation — everywhere else in this
# file, Bill and Vendor Credit map to Cost/Income respectively
# for the *other* Pass Thru accounts, so double-check before
# reusing this table as a template.
LOCK_FEE_TRANSACTION_TYPE_MAP = {
    "revenue recognition": "Income",
    "refund": "Income",
    "credit memo": "Income",
    "bill": "Income",
    "vendor credit": "Income",
    "expense": "Cost",
}

APP_FEE_TRANSACTION_TYPE_MAP = {
    "revenue recognition": "Income",
    "credit memo": "Income",
    "expense": "Cost",
}

# Maintenance accounts are not Income/Cost — we pay the vendor
# (Cost) and bill the owner back by reducing their balance, no
# cash actually changes hands (Billback, displayed via each
# rule's income_label; "Income" is only the internal bucket name
# shared with every other transaction_type_based rule).
#
# Zero-amount rows never affect the P&L either way, so they're
# tagged Cost rather than left blank. Any sign not listed below
# (e.g. a negative Bill, a positive Vendor Credit) doesn't exist
# in the data as of 2026-08-26 — if one appears, it's flagged for
# review rather than guessed.
MAINTENANCE_TRANSACTION_TYPE_SIGN_MAP = {
    "bill": {"positive": "Cost", "zero": "Cost"},
    "expense": {"positive": "Cost", "zero": "Cost"},
    "vendor credit": {"negative": "Income", "zero": "Cost"},
    "journal entry": {
        "positive": "Cost", "zero": "Cost", "negative": "Income"
    },
}

MAINTENANCE_SUB_ACCOUNTS = [
    "Appliances",
    "Electric",
    "HVAC Repairs",
    "Inhouse Repairs",
    "Inventory",
    "Landscape",
    "Plumbing",
    "Pool",
    "Upholstery",
]

ACCOUNT_SPLIT_RULES = [
    {
        "source_account": "Pass Thru Income:Credit Card Clearing",
        "income_label": "Credit Card Income",
        "cost_label": "Credit Card Cost",
        "rule_type": "name_based",
        "cost_name_values": {"Lynnbrook Merchant Services"},
        "allow_manual_tagging": True,
    },
    {
        "source_account": (
            "Pass Thru Income:Housekeeping Clearing"
        ),
        "income_label": "Housekeeping Income",
        "cost_label": "Housekeeping Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_map": HOUSEKEEPING_TRANSACTION_TYPE_MAP,
        # "Journal Entry" is decided by the Amount sign instead
        # of the map above: negative -> Cost, zero or positive
        # -> Income. Zero is not a special case.
        "sign_based_types": {"journal entry"},
    },
    {
        "source_account": "Pass Thru Income:Commission",
        "income_label": "OTA Commission Income",
        "cost_label": "OTA Commission Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_map": (
            OTA_COMMISSION_TRANSACTION_TYPE_MAP
        ),
        # Amount sign is never used for this account — Refunds
        # and Credit Memos stay Income even when negative.
        "sign_based_types": set(),
    },
    {
        "source_account": "Pass Thru Income:HOA Clearing",
        "income_label": "HOA Income",
        "cost_label": "HOA Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_map": HOA_TRANSACTION_TYPE_MAP,
        # Amount sign is never used for this account — negative
        # Credit Memos/Refunds stay Income, and zero-value Bills
        # still classify as Cost like any other Bill.
        "sign_based_types": set(),
    },
    {
        "source_account": (
            "Pass Thru Income:Travel Ins Fee Clearing"
        ),
        "income_label": "Travel Insurance Income",
        "cost_label": "Travel Insurance Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_map": (
            TRAVEL_INSURANCE_TRANSACTION_TYPE_MAP
        ),
        # Amount sign is never used for this account — a
        # negative Refund stays Income, and a zero-value Bill
        # still classifies as Cost like any other Bill.
        "sign_based_types": set(),
    },
    {
        "source_account": "Pass Thru Income:CAM Clearing",
        "income_label": "CAM Income",
        "cost_label": "CAM Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_map": CAM_TRANSACTION_TYPE_MAP,
        # Amount sign is never used for this account — negative
        # Credit Memos/Refunds stay Income, and a zero-value
        # Expense would still classify as Cost like any other
        # Expense.
        "sign_based_types": set(),
    },
    {
        "source_account": "Pass Thru Income:Lock Fee Clearing",
        "income_label": "Lock Fee Income",
        "cost_label": "Lock Fee Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_map": LOCK_FEE_TRANSACTION_TYPE_MAP,
        # Amount sign is never used for this account — negative
        # Refunds/Credit Memos stay Income, and a zero-value row
        # still classifies by its Transaction Type. Bill and
        # Vendor Credit -> Income are provisional — see the map
        # definition above.
        "sign_based_types": set(),
    },
    {
        "source_account": "Pass Thru Income:App Fee",
        "income_label": "App Fee Income",
        "cost_label": "App Fee Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_map": APP_FEE_TRANSACTION_TYPE_MAP,
        # Amount sign is never used for this account — a
        # negative Credit Memo stays Income, and a zero-value
        # row still classifies by its Transaction Type.
        "sign_based_types": set(),
    },
] + [
    {
        "source_account": f"Maintenance:{sub_account}",
        "income_label": f"Maintenance - {sub_account} Billback",
        "cost_label": f"Maintenance - {sub_account} Cost",
        "rule_type": "transaction_type_based",
        "allow_manual_tagging": False,
        "transaction_type_sign_map": (
            MAINTENANCE_TRANSACTION_TYPE_SIGN_MAP
        ),
    }
    for sub_account in MAINTENANCE_SUB_ACCOUNTS
]


# ============================================================
# STEP 3: SOFTWARE ACCOUNT VENDOR REMAPPING
#
# Every row coded to the "Software" account gets its Account
# Name overwritten with one of two targets:
#
#   - Name contains one of the Revenue Management match terms
#     (case-insensitive substring)      -> Revenue Management
#   - everything else, blank Name included -> Software - Other
#
# Only the short Revenue Management list is maintained — the
# long, growing tail of software vendors is swept into
# Software - Other. Nothing is left as bare "Software". The
# match terms and both account names are editable in the UI.
# ============================================================

SOFTWARE_SOURCE_ACCOUNT = "Software"
SOFTWARE_REVENUE_MANAGEMENT_ACCOUNT = "Software - Revenue Management"
SOFTWARE_OTHER_ACCOUNT = "Software - Other"

# Software rows whose Name contains one of these terms
# (case-insensitive) -> Revenue Management. Everything else in the
# Software account -> Software - Other.
DEFAULT_SOFTWARE_REVENUE_MANAGEMENT_TERMS = ["revup"]


def classify_by_transaction_type(rule, transaction_type, amount):
    """
    Centralized classification for every rule_type ==
    "transaction_type_based" account (see ACCOUNT_SPLIT_RULES).

    - If the rule has a "transaction_type_sign_map", look the
      Transaction Type up in it, then look the Amount's sign
      ("positive" / "negative" / "zero") up within that. Missing
      either way returns "" — unclassified, flagged for review.
    - Otherwise, if the (normalized) Transaction Type is listed
      in the rule's "sign_based_types", classify by the Amount
      sign: negative -> Cost, zero or positive -> Income.
    - Otherwise, look the Transaction Type up in the rule's
      "transaction_type_map".
    - If it isn't found any of those ways, return "" —
      unclassified, flagged for review.

    Add a new account by adding a rule + a transaction type map,
    not by writing a new function.
    """

    normalized_type = normalize_text(transaction_type)

    sign_map = rule.get("transaction_type_sign_map")

    if sign_map is not None:

        if amount is None or normalized_type not in sign_map:
            return ""

        if amount > 0:
            sign_key = "positive"
        elif amount < 0:
            sign_key = "negative"
        else:
            sign_key = "zero"

        return sign_map[normalized_type].get(sign_key, "")

    if normalized_type in rule.get("sign_based_types", set()):

        if amount is None:
            return ""

        return "Cost" if amount < 0 else "Income"

    return rule["transaction_type_map"].get(
        normalized_type,
        ""
    )


def get_account_match_mask(df, account_name_col, source_account):
    """
    Boolean mask of rows whose Account Name matches
    source_account exactly (blank-safe, trimmed,
    case-insensitive).
    """

    normalized_target = normalize_account_name(source_account)

    return (
        df[account_name_col]
        .map(normalize_account_name)
        .eq(normalized_target)
    )


def classify_row_for_rule(
    row, rule, name_col, transaction_type_col, amount_col
):
    """
    Classify a single row for one rule. Centralized dispatch by
    rule_type — the only place row-level classification logic
    lives, for both the auto-applied rules and the one rule that
    needs manual review (Credit Card Clearing).

    Returns "Income", "Cost", or "" (unclassified / flagged for
    review).
    """

    if rule["rule_type"] == "name_based":

        name_value = clean_text(row[name_col])

        if name_value == "":
            return ""

        cost_values = {
            normalize_text(value)
            for value in rule["cost_name_values"]
        }

        if normalize_text(name_value) in cost_values:
            return "Cost"

        return "Income"

    if rule["rule_type"] == "transaction_type_based":

        amount = parse_amount(row[amount_col])

        return classify_by_transaction_type(
            rule,
            row[transaction_type_col],
            amount
        )

    return ""


def apply_rule_classification(
    df, rule, matched_index, final_classification, amount_col
):
    """
    Write "Classification" and "Adjusted Amount" for one rule's
    matched rows into df, IN PLACE. Never touches the original
    "Account Name" / "Amount" columns.

    A Cost row whose Amount can't be parsed is left unclassified
    instead of blocking the rest of the rows.

    Returns (parseable_cost_index, income_index,
    unparseable_cost_index).
    """

    income_label = rule["income_label"]
    cost_label = rule["cost_label"]

    final_classification = final_classification.copy()

    cost_index = final_classification[
        final_classification.eq("Cost")
    ].index

    income_index = final_classification[
        final_classification.eq("Income")
    ].index

    parsed_amounts = df.loc[cost_index, amount_col].map(
        parse_amount
    )

    unparseable_cost_index = parsed_amounts[
        parsed_amounts.isna()
    ].index

    parseable_cost_index = parsed_amounts[
        parsed_amounts.notna()
    ].index

    final_classification.loc[unparseable_cost_index] = ""

    df.loc[matched_index, "Classification"] = (
        final_classification.map(
            lambda value: (
                cost_label if value == "Cost"
                else (
                    income_label if value == "Income" else ""
                )
            )
        )
    )

    df.loc[parseable_cost_index, "Adjusted Amount"] = (
        parsed_amounts.loc[parseable_cost_index].map(
            lambda value: f"{-value:.2f}"
        )
    )

    df.loc[income_index, "Adjusted Amount"] = (
        df.loc[income_index, amount_col]
    )

    return parseable_cost_index, income_index, unparseable_cost_index


def build_property_regex(property_name):
    """
    Create a conservative property matching pattern.
    """

    normalized_property = normalize_text(
        property_name
    )

    code_match = re.fullmatch(
        r"(tt|bw|bh|cbs|cr|sk)\s+([a-z0-9]+)",
        normalized_property
    )

    if code_match:

        prefix = re.escape(
            code_match.group(1)
        )

        property_code = re.escape(
            code_match.group(2)
        )

        # Allows TT3 and TT 3
        pattern_body = (
            prefix
            + r"\s*"
            + property_code
        )

    else:

        property_parts = (
            normalized_property.split(" ")
        )

        pattern_body = r"\s+".join(
            re.escape(part)
            for part in property_parts
        )

    complete_pattern = (
        r"(?<![a-z0-9])"
        + pattern_body
        + r"(?![a-z0-9])"
    )

    return re.compile(
        complete_pattern
    )


def prepare_booking_source_text(value):
    """
    Normalize text before searching for booking references.
    """

    text = clean_text(value).upper()

    text = (
        text
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )

    return text


# ============================================================
# MAIN PROCESSING PIPELINE
#
# Wraps everything that used to run top-to-bottom in the Colab
# notebook. Returns a dict of results for the UI to render.
# ============================================================

def process_files(transaction_file, additional_property_file, booking_file):

    log_lines = []

    def log(message):
        log_lines.append(message)

    # --------------------------------------------------------
    # 1-2. READ THE ORIGINAL CSV EXACTLY AS IT APPEARS
    #
    # skip_blank_lines=False preserves completely blank rows.
    # This ensures that rows 1 and 2 are removed based on their
    # actual position in the original CSV.
    # --------------------------------------------------------

    input_filename = transaction_file.name

    raw_df = read_csv_without_header(
        transaction_file,
        skip_blank_lines=False
    )

    log(
        f"Original file dimensions: "
        f"{raw_df.shape[0]} rows × "
        f"{raw_df.shape[1]} columns"
    )

    # --------------------------------------------------------
    # 3. VALIDATE THE ORIGINAL FILE
    # --------------------------------------------------------

    if raw_df.shape[0] < 3:
        raise ValueError(
            "The CSV does not contain enough rows to remove "
            "the first two rows and create headers."
        )

    if raw_df.shape[1] < 2:
        raise ValueError(
            "The CSV does not contain enough columns to remove "
            "the first column."
        )

    # --------------------------------------------------------
    # 4. REMOVE THE ORIGINAL FIRST COLUMN
    # --------------------------------------------------------

    processed_df = raw_df.iloc[:, 1:].copy()

    # --------------------------------------------------------
    # 5. REMOVE THE ORIGINAL FIRST TWO ROWS
    # --------------------------------------------------------

    processed_df = processed_df.iloc[2:].copy()

    # --------------------------------------------------------
    # 6. MAKE THE FIRST REMAINING ROW THE HEADER ROW
    # --------------------------------------------------------

    new_headers = (
        processed_df.iloc[0]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    processed_df = processed_df.iloc[1:].copy()
    processed_df.columns = new_headers
    processed_df.reset_index(drop=True, inplace=True)

    # --------------------------------------------------------
    # 7. LOCATE THE REQUIRED TRANSACTION COLUMNS
    # --------------------------------------------------------

    transaction_date_column = find_column(
        processed_df,
        "Transaction date"
    )

    account_name_column = find_column(
        processed_df,
        "Account Name"
    )

    class_full_name_column = find_column(
        processed_df,
        "Class full name"
    )

    description_column = find_column(
        processed_df,
        "Description"
    )

    num_column = find_column(
        processed_df,
        "Num"
    )

    amount_column = find_column(
        processed_df,
        "Amount"
    )

    # --------------------------------------------------------
    # 8. REMOVE ROWS WHERE TRANSACTION DATE IS BLANK
    #
    # This removes:
    # - Category headings
    # - Subtotals
    # - Totals
    # - Other non-transaction rows
    #
    # The row is removed even when another field contains a
    # label or an amount.
    # --------------------------------------------------------

    rows_before_transaction_filter = len(processed_df)

    transaction_date_values = (
        processed_df[transaction_date_column]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    processed_df = processed_df[
        transaction_date_values.ne("")
    ].copy()

    processed_df.reset_index(drop=True, inplace=True)

    rows_removed_for_blank_transaction_date = (
        rows_before_transaction_filter
        - len(processed_df)
    )

    # --------------------------------------------------------
    # 8b. NORMALIZE THE AMOUNT COLUMN
    #
    # Every Amount value is rewritten as a plain number with two
    # decimals — no "$", no thousands commas. Blank values stay
    # blank. Values that cannot be parsed as a number are left
    # untouched and counted below.
    # --------------------------------------------------------

    def format_amount(value):

        text = clean_text(value)

        if text == "":
            return ""

        parsed = parse_amount(text)

        if parsed is None:
            return text

        return f"{parsed:.2f}"

    original_amount_values = (
        processed_df[amount_column]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    unparseable_amount_count = int(
        (
            original_amount_values.ne("")
            & original_amount_values.map(parse_amount).isna()
        ).sum()
    )

    processed_df[amount_column] = (
        processed_df[amount_column].map(format_amount)
    )

    # --------------------------------------------------------
    # 9-12. READ AND COMBINE THE ADDITIONAL PROPERTY LIST
    #
    # The CSV should contain one property column.
    #
    # It may have a header such as:
    # - Property
    # - Properties
    # - Property Name
    #
    # A header is not required.
    # --------------------------------------------------------

    additional_property_raw_df = read_csv_without_header(
        additional_property_file,
        skip_blank_lines=False
    )

    if additional_property_raw_df.empty:
        raise ValueError(
            "The uploaded additional property-list CSV is empty."
        )

    # Find columns that contain at least one nonblank value
    nonblank_property_columns = []

    for column in additional_property_raw_df.columns:

        cleaned_column_values = (
            additional_property_raw_df[column]
            .fillna("")
            .astype(str)
            .map(clean_text)
        )

        if cleaned_column_values.ne("").any():
            nonblank_property_columns.append(column)

    if not nonblank_property_columns:
        raise ValueError(
            "No property values were found in the additional "
            "property-list CSV."
        )

    if len(nonblank_property_columns) > 1:
        log(
            "Warning: The additional property CSV contains more "
            "than one nonblank column. The first nonblank column "
            "will be used."
        )

    additional_property_column = nonblank_property_columns[0]

    additional_properties = (
        additional_property_raw_df[additional_property_column]
        .fillna("")
        .astype(str)
        .map(clean_text)
        .tolist()
    )

    # Remove a possible header from the first row
    possible_property_headers = {
        "property",
        "properties",
        "property name",
        "property names"
    }

    if additional_properties:

        first_value_normalized = normalize_text(
            additional_properties[0]
        )

        if first_value_normalized in possible_property_headers:
            additional_properties = additional_properties[1:]

    # Remove blanks and non-property values
    invalid_property_values = {
        "",
        "fvrc",
        "bri"
    }

    additional_properties = [
        property_name
        for property_name in additional_properties
        if normalize_text(property_name)
        not in invalid_property_values
    ]

    # Combine the base and additional property lists.
    #
    # Duplicate matching ignores capitalization and extra spaces.
    # If a duplicate appears in both lists, the spelling from the
    # base list is preserved.

    combined_property_dictionary = {}

    for property_name in BASE_PROPERTIES:

        normalized_property = normalize_text(property_name)

        if normalized_property not in invalid_property_values:

            combined_property_dictionary[
                normalized_property
            ] = property_name

    base_property_count = len(
        combined_property_dictionary
    )

    for property_name in additional_properties:

        normalized_property = normalize_text(property_name)

        if (
            normalized_property not in invalid_property_values
            and normalized_property
            not in combined_property_dictionary
        ):

            combined_property_dictionary[
                normalized_property
            ] = property_name

    combined_properties = list(
        combined_property_dictionary.values()
    )

    combined_property_count = len(
        combined_properties
    )

    new_uploaded_property_count = (
        combined_property_count
        - base_property_count
    )

    # --------------------------------------------------------
    # 13-14. READ AND VALIDATE THE BOOKING-TO-PROPERTY CSV
    #
    # Required columns:
    # - Lease ID
    # - Unit Name
    # --------------------------------------------------------

    booking_lookup_df = read_csv_with_header(
        booking_file
    )

    lease_id_column = find_column(
        booking_lookup_df,
        "Lease ID"
    )

    unit_name_column = find_column(
        booking_lookup_df,
        "Unit Name"
    )

    booking_lookup_df[lease_id_column] = (
        booking_lookup_df[lease_id_column]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    booking_lookup_df[unit_name_column] = (
        booking_lookup_df[unit_name_column]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    # Remove rows with no Lease ID
    booking_lookup_df = booking_lookup_df[
        booking_lookup_df[lease_id_column].ne("")
    ].copy()

    booking_lookup_df.reset_index(
        drop=True,
        inplace=True
    )

    # --------------------------------------------------------
    # 15. BUILD THE OFFICIAL BOOKING LOOKUP
    #
    # A Lease ID may appear more than once in the uploaded file.
    #
    # If the same Lease ID is associated with:
    # - The same Unit Name repeatedly: it remains valid
    # - Multiple different Unit Names: its property is
    #   considered ambiguous and will not be guessed
    # --------------------------------------------------------

    booking_units_by_id = defaultdict(set)
    official_booking_display = {}

    for _, row in booking_lookup_df.iterrows():

        lease_id = clean_text(
            row[lease_id_column]
        )

        unit_name = clean_text(
            row[unit_name_column]
        )

        normalized_lease_id = normalize_booking_id(
            lease_id
        )

        if normalized_lease_id == "":
            continue

        if normalized_lease_id not in official_booking_display:

            official_booking_display[
                normalized_lease_id
            ] = normalize_booking_id(lease_id)

        if unit_name != "":

            booking_units_by_id[
                normalized_lease_id
            ].add(unit_name)

    # Official Lease ID to Property mapping
    official_booking_to_property = {}

    ambiguous_booking_ids = set()

    for booking_id, unit_names in booking_units_by_id.items():

        if len(unit_names) == 1:

            official_booking_to_property[
                booking_id
            ] = next(iter(unit_names))

        elif len(unit_names) > 1:

            ambiguous_booking_ids.add(
                booking_id
            )

    official_booking_ids = set(
        official_booking_display.keys()
    )

    # --------------------------------------------------------
    # 16. INDEX OFFICIAL BOOKINGS BY THEIR LEADING NUMBER
    #
    # Examples:
    #
    # 107988-HMYJZJXPCZ
    # 107988
    #
    # Both have the leading booking number 107988.
    #
    # Five-digit IDs are also supported when they exist in the
    # official booking file.
    # --------------------------------------------------------

    booking_ids_by_base_number = defaultdict(list)

    for booking_id in official_booking_ids:

        base_match = re.match(
            r"^(\d{5,6})(?:-|$)",
            booking_id
        )

        if base_match:

            base_number = base_match.group(1)

            booking_ids_by_base_number[
                base_number
            ].append(booking_id)

    # Sort booking IDs to make results consistent
    for base_number in booking_ids_by_base_number:

        booking_ids_by_base_number[
            base_number
        ] = sorted(
            booking_ids_by_base_number[
                base_number
            ]
        )

    def resolve_booking_candidate(base_number, suffix=""):
        """
        Resolve one possible booking reference.

        Priority:
        1. Exact official Lease ID
        2. Unique official Lease ID starting with the prefix
        3. Exact official base booking
        4. Unique official Lease ID sharing the base number
        5. Unvalidated complete booking reference
        6. Unvalidated six-digit booking number

        Returns:
            booking_value
            quality_score
        """

        base_number = clean_text(
            base_number
        )

        suffix = clean_text(
            suffix
        ).upper()

        if suffix != "":

            candidate = normalize_booking_id(
                f"{base_number}-{suffix}"
            )

        else:

            candidate = normalize_booking_id(
                base_number
            )

        # Exact official Lease ID
        if candidate in official_booking_ids:

            return (
                official_booking_display[candidate],
                100
            )

        official_base_candidates = (
            booking_ids_by_base_number.get(
                base_number,
                []
            )
        )

        # Unique official Lease ID beginning with an incomplete
        # prefix such as 107938-HM3
        if suffix != "":

            prefix_matches = [
                booking_id
                for booking_id
                in official_base_candidates
                if booking_id.startswith(candidate)
            ]

            if len(prefix_matches) == 1:

                resolved_booking = prefix_matches[0]

                return (
                    official_booking_display[
                        resolved_booking
                    ],
                    90
                )

        # Exact official base booking such as 107964
        normalized_base = normalize_booking_id(
            base_number
        )

        if normalized_base in official_booking_ids:

            return (
                official_booking_display[
                    normalized_base
                ],
                85
            )

        # Only one official Lease ID has this base number
        if len(official_base_candidates) == 1:

            resolved_booking = (
                official_base_candidates[0]
            )

            return (
                official_booking_display[
                    resolved_booking
                ],
                80
            )

        # Multiple official Lease IDs share the same base
        # number. Keep the base number but do not guess which
        # full booking.
        if len(official_base_candidates) > 1:

            return (
                base_number,
                40
            )

        # Complete-looking booking not found in the uploaded
        # file. Ten-character and longer alphanumeric suffixes
        # are kept. This also supports examples whose suffix is
        # longer than ten characters.
        if suffix != "" and len(suffix) >= 10:

            return (
                candidate,
                30
            )

        # Unmatched six-digit booking number
        if len(base_number) == 6:

            return (
                base_number,
                20
            )

        # Five-digit values are retained only if they were
        # present in the official booking file.
        if base_number in booking_ids_by_base_number:

            return (
                base_number,
                15
            )

        return ("", -1)

    def extract_best_booking_from_text(value):
        """
        Extract the strongest booking candidate from one text
        field.
        """

        text = prepare_booking_source_text(
            value
        )

        if text == "":
            return ("", -1)

        results = []

        # Finds five- or six-digit leading booking numbers.
        #
        # Five-digit values are accepted only when supported by
        # the official booking file.
        booking_number_pattern = re.compile(
            r"(?<!\d)(\d{5,6})(?!\d)"
        )

        for match in booking_number_pattern.finditer(text):

            base_number = match.group(1)

            text_after_number = text[
                match.end():
            ]

            # Capture a possible alphanumeric suffix after a
            # hyphen.
            #
            # Examples:
            # -HM3
            # -HMYJZJXPCZ
            # -REV
            suffix_match = re.match(
                r"\s*-\s*([A-Z0-9]+)",
                text_after_number
            )

            suffix = ""

            if suffix_match:
                suffix = suffix_match.group(1)

            booking_value, quality_score = (
                resolve_booking_candidate(
                    base_number,
                    suffix
                )
            )

            if booking_value != "":

                results.append(
                    (
                        booking_value,
                        quality_score,
                        match.start()
                    )
                )

        if not results:
            return ("", -1)

        # Highest-quality match first.
        # If quality is tied, use the earliest match in the
        # text.
        results.sort(
            key=lambda result: (
                -result[1],
                result[2]
            )
        )

        best_booking_value = results[0][0]
        best_quality_score = results[0][1]

        return (
            best_booking_value,
            best_quality_score
        )

    def extract_booking_from_row(row):
        """
        Search the three booking source fields.

        Field priority:
        1. Num
        2. Class full name
        3. Description

        A higher-quality official match can override a weaker
        unvalidated candidate from an earlier field.
        """

        source_columns = [
            num_column,
            class_full_name_column,
            description_column
        ]

        best_booking = ""
        best_score = -1

        for source_column in source_columns:

            booking_value, score = (
                extract_best_booking_from_text(
                    row[source_column]
                )
            )

            if score > best_score:

                best_booking = booking_value
                best_score = score

        return best_booking

    def extract_property_from_description(description):
        """
        Search Description for a recognized property.

        Returns the standardized property name from the
        combined property list.

        Returns blank if no recognized property appears.
        """

        normalized_description = normalize_text(
            description
        )

        if normalized_description == "":
            return ""

        for property_name, property_pattern in property_patterns:

            if property_pattern.search(
                normalized_description
            ):
                return property_name

        return ""

    def get_property_from_booking(booking_value):
        """
        Return Unit Name for an official unambiguous Lease ID.

        Otherwise return Unknown.
        """

        normalized_booking = normalize_booking_id(
            booking_value
        )

        if normalized_booking == "":
            return "Unknown"

        if normalized_booking in ambiguous_booking_ids:
            return "Unknown"

        property_name = official_booking_to_property.get(
            normalized_booking,
            ""
        )

        if clean_text(property_name) == "":
            return "Unknown"

        return clean_text(property_name)

    # --------------------------------------------------------
    # 17. CREATE THE NEW OUTPUT COLUMNS
    #
    # Owner Name is intentionally excluded for now.
    # --------------------------------------------------------

    processed_df["Property"] = ""
    processed_df["Booking"] = ""

    # --------------------------------------------------------
    # 18. CORPORATE ACCOUNT TAGGING
    # --------------------------------------------------------

    normalized_corporate_accounts = {
        normalize_account_name(account_name)
        for account_name in CORPORATE_ACCOUNT_NAMES
    }

    normalized_account_values = (
        processed_df[account_name_column]
        .fillna("")
        .astype(str)
        .map(normalize_account_name)
    )

    corporate_mask = normalized_account_values.isin(
        normalized_corporate_accounts
    )

    processed_df.loc[
        corporate_mask,
        ["Property", "Booking"]
    ] = "Corporate"

    # --------------------------------------------------------
    # 19. PROPERTY EXTRACTION STEP 1:
    #     PROPERTY FROM CLASS FULL NAME
    #
    # This runs only for non-Corporate rows.
    #
    # Rules:
    # - Blank = do not use
    # - FVRC = do not use
    # - BRI = do not use
    # - Every other nonblank Class full name = Property
    # --------------------------------------------------------

    class_values = (
        processed_df[class_full_name_column]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    normalized_class_values = (
        class_values.map(normalize_text)
    )

    invalid_class_values = {
        "",
        "fvrc",
        "bri"
    }

    valid_class_property_mask = (
        ~corporate_mask
        & ~normalized_class_values.isin(
            invalid_class_values
        )
    )

    processed_df.loc[
        valid_class_property_mask,
        "Property"
    ] = class_values[
        valid_class_property_mask
    ]

    # --------------------------------------------------------
    # 20. BUILD PROPERTY-MATCHING PATTERNS FOR DESCRIPTION
    #
    # Matching:
    # - Ignores capitalization
    # - Ignores repeated spaces
    # - Prefers longer and more specific properties
    # - Recognizes formats such as TT3 and TT 3
    # - Does not guess when no valid property is found
    # --------------------------------------------------------

    # Longer property names are checked first
    sorted_properties_for_matching = sorted(
        combined_properties,
        key=lambda property_name: (
            len(normalize_text(property_name)),
            len(
                normalize_text(property_name).split()
            )
        ),
        reverse=True
    )

    property_patterns = [
        (
            property_name,
            build_property_regex(property_name)
        )
        for property_name
        in sorted_properties_for_matching
    ]

    # --------------------------------------------------------
    # 21. PROPERTY EXTRACTION STEP 2:
    #     PROPERTY FROM DESCRIPTION
    #
    # This runs only when:
    # - The row is not Corporate
    # - Property is still blank
    # --------------------------------------------------------

    property_blank_before_description = (
        processed_df["Property"]
        .fillna("")
        .astype(str)
        .map(clean_text)
        .eq("")
    )

    description_property_candidate_mask = (
        ~corporate_mask
        & property_blank_before_description
    )

    description_property_matches = (
        processed_df.loc[
            description_property_candidate_mask,
            description_column
        ]
        .fillna("")
        .astype(str)
        .map(extract_property_from_description)
    )

    processed_df.loc[
        description_property_candidate_mask,
        "Property"
    ] = description_property_matches

    # --------------------------------------------------------
    # 22-23. EXTRACT BOOKING FOR STILL-UNRESOLVED ROWS
    #
    # This runs only when:
    # - The row is not Corporate
    # - Property remains blank after Class and Description
    #   mapping
    #
    # Booking references may appear in:
    #
    # 1. Num
    # 2. Class full name
    # 3. Description
    #
    # Examples:
    #
    # 107669 CM
    # 103938RR
    # Invoice 107874-HM5 RR
    # 103548-Rev-2026-02-28
    # 107938-HM3-2026-01-31
    # 107988-HMYJZJXPCZ
    # 107980-HM5B4P9JCM
    #
    # The booking lookup file is used as the source of truth.
    # --------------------------------------------------------

    property_blank_before_booking = (
        processed_df["Property"]
        .fillna("")
        .astype(str)
        .map(clean_text)
        .eq("")
    )

    booking_candidate_mask = (
        ~corporate_mask
        & property_blank_before_booking
    )

    processed_df.loc[
        booking_candidate_mask,
        "Booking"
    ] = processed_df.loc[
        booking_candidate_mask
    ].apply(
        extract_booking_from_row,
        axis=1
    )

    # --------------------------------------------------------
    # 24. POPULATE PROPERTY FROM THE CONFIRMED BOOKING
    #
    # Exact or uniquely resolved official bookings use Unit
    # Name.
    #
    # If the booking cannot be mapped to one Unit Name:
    # Property = Unknown
    #
    # If no booking can be extracted:
    # Property = Unknown
    # --------------------------------------------------------

    processed_df.loc[
        booking_candidate_mask,
        "Property"
    ] = processed_df.loc[
        booking_candidate_mask,
        "Booking"
    ].map(
        get_property_from_booking
    )

    # --------------------------------------------------------
    # 25. FINAL SAFETY CHECK
    #
    # Any non-Corporate row that somehow still has a blank
    # Property is labeled Unknown.
    # --------------------------------------------------------

    final_blank_property_mask = (
        ~corporate_mask
        & processed_df["Property"]
            .fillna("")
            .astype(str)
            .map(clean_text)
            .eq("")
    )

    processed_df.loc[
        final_blank_property_mask,
        "Property"
    ] = "Unknown"

    # --------------------------------------------------------
    # 26. SUMMARY STATISTICS
    # --------------------------------------------------------

    corporate_row_count = int(
        corporate_mask.sum()
    )

    property_from_class_count = int(
        valid_class_property_mask.sum()
    )

    property_from_description_count = int(
        description_property_matches
        .fillna("")
        .astype(str)
        .map(clean_text)
        .ne("")
        .sum()
    )

    booking_extracted_count = int(
        (
            booking_candidate_mask
            & processed_df["Booking"]
                .fillna("")
                .astype(str)
                .map(clean_text)
                .ne("")
        ).sum()
    )

    property_from_booking_count = int(
        (
            booking_candidate_mask
            & ~processed_df["Property"].eq("Unknown")
        ).sum()
    )

    unknown_property_count = int(
        processed_df["Property"]
        .eq("Unknown")
        .sum()
    )

    ambiguous_booking_count = len(
        ambiguous_booking_ids
    )

    stats = {
        "Original file dimensions": (
            f"{raw_df.shape[0]} rows × {raw_df.shape[1]} columns"
        ),
        "Final file dimensions": (
            f"{processed_df.shape[0]} rows × "
            f"{processed_df.shape[1]} columns"
        ),
        "Rows removed (blank Transaction date)": (
            rows_removed_for_blank_transaction_date
        ),
        "Base valid properties": base_property_count,
        "New unique properties from uploaded list": (
            new_uploaded_property_count
        ),
        "Total combined valid properties": (
            combined_property_count
        ),
        "Official Lease IDs loaded": len(official_booking_ids),
        "Lease IDs with conflicting Unit Names": (
            ambiguous_booking_count
        ),
        "Corporate rows": corporate_row_count,
        "Properties populated from Class full name": (
            property_from_class_count
        ),
        "Properties populated from Description": (
            property_from_description_count
        ),
        "Bookings extracted for unresolved rows": (
            booking_extracted_count
        ),
        "Properties populated from Booking": (
            property_from_booking_count
        ),
        "Rows tagged as Unknown Property": (
            unknown_property_count
        ),
        "Amount values that could not be normalized": (
            unparseable_amount_count
        ),
    }

    # --------------------------------------------------------
    # UNKNOWN PROPERTY ROWS FOR REVIEW
    # --------------------------------------------------------

    mapping_preview_columns = [
        transaction_date_column,
        account_name_column,
        num_column,
        class_full_name_column,
        description_column,
        "Property",
        "Booking"
    ]

    unknown_review_df = processed_df[
        processed_df["Property"].eq("Unknown")
    ][mapping_preview_columns].copy()

    # --------------------------------------------------------
    # COMBINED PROPERTY-LIST OUTPUT
    # --------------------------------------------------------

    combined_property_df = pd.DataFrame({
        "Property": combined_properties
    })

    # --------------------------------------------------------
    # OUTPUT FILE NAMES
    # --------------------------------------------------------

    input_name_without_extension = os.path.splitext(
        input_filename
    )[0]

    output_filename = (
        f"{input_name_without_extension}_mapped.csv"
    )

    property_list_output_filename = (
        f"{input_name_without_extension}"
        f"_combined_property_list.csv"
    )

    unknown_output_filename = (
        f"{input_name_without_extension}"
        f"_unknown_property_review.csv"
    )

    return {
        "log_lines": log_lines,
        "stats": stats,
        "processed_df": processed_df,
        "mapping_preview_columns": mapping_preview_columns,
        "unknown_review_df": unknown_review_df,
        "combined_property_df": combined_property_df,
        "output_filename": output_filename,
        "property_list_output_filename": (
            property_list_output_filename
        ),
        "unknown_output_filename": unknown_output_filename,
        "transaction_date_column": transaction_date_column,
        "account_name_column": account_name_column,
        "class_full_name_column": class_full_name_column,
        "description_column": description_column,
        "num_column": num_column,
        "amount_column": amount_column,
    }


# ============================================================
# STEP 1B: OWNER NAME MATCHING
#
# Last resort for rows still tagged "Unknown" after Step 1's
# Class / Description / Booking cascade. An uploaded Owner CSV
# (Owner First Name, Owner Last Name, Unit Name — one row per
# property an owner holds) is checked against each Unknown row's
# Name, then Description if Name has no match.
#
# A match requires the owner's first AND last name to each
# appear as a whole word somewhere in the (normalized) field —
# in any order, ignoring extra words. This assumes single-word
# first/last names; a multi-word surname is not handled.
#
# This never decides anything by itself — see the Streamlit
# section below for the confirm-before-apply UI. It only reports
# candidates.
# ============================================================

def normalize_name_tokens(value):
    """
    Whole-word token set for owner-name matching (blank-safe).
    """

    normalized = normalize_text(value)

    if normalized == "":
        return set()

    return set(normalized.split())


def match_owner_candidates(text_tokens, owner_records):
    """
    Every owner_records entry is (first_token, last_token,
    display_name, unit_name). Returns (matched_owner_display_names,
    candidate_unit_names) for every owner whose first AND last
    token both appear in text_tokens — both sorted and
    deduplicated. A single owner with several units, and two
    different owners who share a name, come back the same way:
    as more than one candidate unit name.
    """

    matched_owners = set()
    candidate_units = set()

    for first_token, last_token, display_name, unit_name in (
        owner_records
    ):

        if first_token in text_tokens and last_token in text_tokens:
            matched_owners.add(display_name)
            candidate_units.add(unit_name)

    return sorted(matched_owners), sorted(candidate_units)


def find_owner_match_for_row(
    name_value, description_value, owner_records
):
    """
    Try Name first; Description is only checked when Name finds
    nothing. Returns (matched_field, matched_owner_display_names,
    candidate_unit_names) — matched_field is "" when neither
    field matched any owner.
    """

    name_matched_owners, name_candidate_units = (
        match_owner_candidates(
            normalize_name_tokens(name_value), owner_records
        )
    )

    if name_candidate_units:
        return "Name", name_matched_owners, name_candidate_units

    description_matched_owners, description_candidate_units = (
        match_owner_candidates(
            normalize_name_tokens(description_value),
            owner_records
        )
    )

    if description_candidate_units:
        return (
            "Description", description_matched_owners,
            description_candidate_units
        )

    return "", [], []


# ============================================================
# STREAMLIT PAGE
# ============================================================

st.set_page_config(
    page_title="SOS P&L Data Prep",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 4rem;
    max-width: 1150px;
}

/* Hero */
.hps-hero h1 {
    font-size: 2.05rem;
    font-weight: 750;
    margin-bottom: 0.1rem;
    letter-spacing: -0.02em;
}
.hps-hero p {
    font-size: 1.02rem;
    opacity: 0.72;
    margin-top: 0;
    margin-bottom: 1.6rem;
}

/* Upload cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
}
div[data-testid="stFileUploaderDropzone"] {
    border-radius: 10px;
}

.status-pill {
    display: inline-block;
    padding: 0.18rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-top: 0.35rem;
}
.status-pending {
    background: rgba(128, 128, 128, 0.15);
    opacity: 0.75;
}
.status-done {
    background: rgba(16, 185, 129, 0.16);
    color: #10b981;
}

/* Primary run button */
div[data-testid="stButton"] button[kind="primary"] {
    border-radius: 999px;
    padding: 0.55rem 2.2rem;
    font-weight: 650;
    font-size: 1.02rem;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

/* Download buttons */
div[data-testid="stDownloadButton"] button {
    border-radius: 10px;
    font-weight: 600;
    width: 100%;
}

/* Dataframes */
div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

/* "Where do I get this file?" expanders */
div[data-testid="stExpander"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(128, 128, 128, 0.25);
}
div[data-testid="stExpander"] summary {
    font-size: 0.88rem;
    font-weight: 600;
    opacity: 0.85;
}

/* Metrics */
div[data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.06);
    border-radius: 12px;
    padding: 0.9rem 1rem 0.6rem 1rem;
}

hr {
    margin: 1.6rem 0;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if "uploader_version" not in st.session_state:
    st.session_state["uploader_version"] = 0

uploader_version = st.session_state["uploader_version"]

with st.sidebar:
    st.markdown("### 🏢 SOS P&L Data Prep")
    st.caption(
        "FVRC transaction cleaning & property/booking mapping"
    )
    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. Upload the three CSVs\n"
        "2. Click **Run processing**\n"
        "3. Review results and download"
    )
    st.divider()
    st.caption(
        "Everything runs locally in this session — no data is "
        "stored or sent anywhere else."
    )

st.markdown(
    '<div class="hps-hero">'
    '<h1>SOS - Property-Level P&amp;L Data Preparation Tool</h1>'
    '<p>Clean the transaction export and map every row to a '
    'Property and Booking.</p>'
    '</div>',
    unsafe_allow_html=True
)

TRANSACTION_HELP_MARKDOWN = """
**Where to get it:**
1. QuickBooks Online → **Reports** → **Custom Reports**
2. Open your saved custom report **P&L GL Detail**
   (or search "Profit and Loss Detail" and customize it)
3. Set the date range, then **Export to Excel/CSV**

**Columns needed** (any order):
- Transaction date
- Account Name
- Class full name
- Description
- Num
- Amount
- Name
- Customer
- Transaction Type
"""

PROPERTY_HELP_MARKDOWN = """
**Where to get it:**
1. Open the most recent **Unit Economics** file
2. Go to the **Property Dimension** tab
3. Copy the **Unit Name** column into a CSV — one property
   per row

**Columns needed:**
- One column of property names (header optional)

💡 Only needed for properties not already built into this
tool — existing ones don't need to be re-uploaded.
"""

BOOKING_HELP_MARKDOWN = """
**Where to get it:**
1. Streamline → **Reports** → **Reservation Analysis Report**
2. Pull **full historical data**, plus **at least 6 months
   into the future** — future bookings can already affect
   today's books (e.g. long stays), so they need to be
   included too
3. Export to CSV

**Columns needed:**
- Lease ID
- Unit Name
"""

OWNER_HELP_MARKDOWN = """
**Where to get it:**
1. Open the latest **Property Level P&L** (Google Sheets)
2. Go to the **Unique Properties with Owners** tab — it lists
   every unique property with its owner, with columns
   Owner First Name, Owner Last Name, Unit Name
3. **File → Download → Comma-separated values (.csv)** to
   download that tab

**Columns needed** (any order):
- Owner First Name
- Owner Last Name
- Unit Name

One row per property an owner holds — an owner with three units
appears as three rows.

💡 Optional. Only used to try matching rows still tagged
Unknown after Property, Description, and Booking matching.
"""

file_specs = [
    (
        "📄",
        "Transaction CSV",
        "Original FVRC Profit and Loss Detail export",
        f"transaction_file_{uploader_version}",
        TRANSACTION_HELP_MARKDOWN
    ),
    (
        "🏘️",
        "Property list",
        "Additional one-column property list",
        f"property_file_{uploader_version}",
        PROPERTY_HELP_MARKDOWN
    ),
    (
        "🔗",
        "Booking lookup",
        "CSV with 'Lease ID' and 'Unit Name'",
        f"booking_file_{uploader_version}",
        BOOKING_HELP_MARKDOWN
    ),
]

upload_cols = st.columns(3)
uploaded_files = {}

for col, (icon, title, help_text, widget_key, help_markdown) in zip(
    upload_cols, file_specs
):
    with col:
        with st.container(border=True):
            st.markdown(f"**{icon} {title}**")
            st.caption(help_text)

            with st.expander("📍 Where do I get this file?"):
                st.markdown(help_markdown)

            uploaded_file = st.file_uploader(
                title,
                type="csv",
                key=widget_key,
                label_visibility="collapsed"
            )

            if uploaded_file:
                st.markdown(
                    '<span class="status-pill status-done">'
                    '✓ Uploaded</span>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<span class="status-pill status-pending">'
                    'Pending</span>',
                    unsafe_allow_html=True
                )

            uploaded_files[widget_key] = uploaded_file

transaction_file = uploaded_files[
    f"transaction_file_{uploader_version}"
]
property_file = uploaded_files[
    f"property_file_{uploader_version}"
]
booking_file = uploaded_files[
    f"booking_file_{uploader_version}"
]

all_files_uploaded = bool(
    transaction_file and property_file and booking_file
)

st.write("")

_, run_col, _ = st.columns([1, 1.2, 1])

with run_col:
    run_clicked = st.button(
        "▶  Run processing",
        type="primary",
        use_container_width=True,
        disabled=not all_files_uploaded
    )

if not all_files_uploaded:
    st.caption(
        "Upload all three files above to enable processing."
    )

if run_clicked:

    with st.spinner("Processing transactions..."):

        try:
            results = process_files(
                transaction_file,
                property_file,
                booking_file
            )
            st.session_state["sos_results"] = results

            # A fresh Step 1 result invalidates any in-progress
            # Step 1B/2/3 work (it was built from the previous
            # dataframe) — clear it so later steps can't silently
            # keep operating on stale data.
            for key in list(st.session_state.keys()):
                if (
                    key in ("stage2_df", "stage3_df")
                    or key.startswith("stage2_")
                    or key.startswith("stage3_")
                    or key.startswith("owner_match_")
                ):
                    del st.session_state[key]

        except (ValueError, KeyError) as error:
            st.session_state.pop("sos_results", None)
            st.error(str(error))

if "sos_results" in st.session_state:

    results = st.session_state["sos_results"]
    stats = results["stats"]

    st.divider()

    header_col, reset_col = st.columns([5, 1])

    with header_col:
        st.subheader("✅ Processing completed")

    with reset_col:
        if st.button("🔄 Start over", use_container_width=True):
            for key in list(st.session_state.keys()):
                if (
                    key == "sos_results"
                    or key.startswith("stage2_")
                    or key.startswith("stage3_")
                    or key.startswith("owner_match_")
                ):
                    del st.session_state[key]
            st.session_state["uploader_version"] += 1
            st.rerun()

    total_rows = len(results["processed_df"])
    unknown_rows = stats["Rows tagged as Unknown Property"]
    match_rate = (
        100.0 * (total_rows - unknown_rows) / total_rows
        if total_rows else 0.0
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows processed", f"{total_rows:,}")
    m2.metric("Corporate rows", f"{stats['Corporate rows']:,}")
    m3.metric("Unknown property rows", f"{unknown_rows:,}")
    m4.metric("Match rate", f"{match_rate:.1f}%")

    (
        tab_summary,
        tab_data,
        tab_mapping,
        tab_unknown,
        tab_downloads
    ) = st.tabs(
        [
            "📊 Summary",
            "🧾 Processed Data",
            "🗺️ Mapping Preview",
            "❓ Unknown Rows",
            "⬇️ Downloads"
        ]
    )

    with tab_summary:

        for log_line in results["log_lines"]:
            st.write(log_line)

        stats_df = pd.DataFrame(
            stats.items(),
            columns=["Metric", "Value"]
        )
        st.dataframe(
            stats_df,
            use_container_width=True,
            hide_index=True
        )

    with tab_data:
        st.dataframe(
            results["processed_df"],
            use_container_width=True,
            height=440
        )

    with tab_mapping:
        st.dataframe(
            results["processed_df"][
                results["mapping_preview_columns"]
            ],
            use_container_width=True,
            height=440
        )

    with tab_unknown:
        if unknown_rows:
            st.warning(
                f"{unknown_rows} row(s) could not be matched "
                "to a known property. Review below."
            )
        else:
            st.success("No unresolved rows.")

        st.dataframe(
            results["unknown_review_df"],
            use_container_width=True,
            height=440
        )

    with tab_downloads:

        d1, d2, d3 = st.columns(3)

        with d1:
            st.download_button(
                "⬇️ Processed CSV",
                data=results["processed_df"].to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name=results["output_filename"],
                mime="text/csv",
                use_container_width=True
            )

        with d2:
            st.download_button(
                "⬇️ Combined property list",
                data=results["combined_property_df"].to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name=(
                    results["property_list_output_filename"]
                ),
                mime="text/csv",
                use_container_width=True
            )

        with d3:
            st.download_button(
                "⬇️ Unknown-property review",
                data=results["unknown_review_df"].to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name=results["unknown_output_filename"],
                mime="text/csv",
                use_container_width=True
            )

    # ========================================================
    # STEP 1B — OWNER NAME MATCHING
    #
    # Optional last resort for rows still tagged "Unknown". See
    # find_owner_match_for_row() / match_owner_candidates() above
    # for the matching rule. Nothing is auto-applied here — every
    # proposed match needs an explicit confirm before "Apply".
    # ========================================================

    st.divider()
    st.header("🔗 Step 1B — Owner Name Matching")
    st.caption(
        "Optional last resort for rows still tagged Unknown. "
        "Every match is proposed, never assumed — you confirm "
        "each one."
    )

    if "owner_match_df" not in st.session_state:
        st.session_state["owner_match_df"] = (
            results["processed_df"].copy()
        )

    owner_match_df = st.session_state["owner_match_df"]

    owner_file = st.file_uploader(
        "Owner CSV — Owner First Name, Owner Last Name, "
        "Unit Name",
        type="csv",
        key="owner_match_uploader"
    )

    with st.expander("📍 Where do I get this file?"):
        st.markdown(OWNER_HELP_MARKDOWN)

    skip_col, undo_col = st.columns([1, 3])

    with skip_col:
        if st.button(
            "Skip this step", key="owner_match_skip_button"
        ):
            st.session_state["owner_match_skipped"] = True

    if st.session_state.get("owner_match_skipped", False):

        with undo_col:
            if st.button(
                "Show matching instead",
                key="owner_match_undo_skip_button"
            ):
                st.session_state["owner_match_skipped"] = False
                st.rerun()

        st.info(
            "Skipped — every remaining row stays exactly "
            "Unknown."
        )

    elif owner_file is None:
        st.caption(
            "Upload an Owner CSV to try matching the remaining "
            "Unknown rows by name."
        )

    else:

        owner_df = None

        try:
            owner_df = read_csv_with_header(owner_file)
            owner_first_col = find_column(
                owner_df, "Owner First Name"
            )
            owner_last_col = find_column(
                owner_df, "Owner Last Name"
            )
            owner_unit_col = find_column(owner_df, "Unit Name")
            owner_match_name_col = find_column(
                owner_match_df, "Name"
            )
            owner_match_description_col = (
                results["description_column"]
            )

        except KeyError as error:
            owner_df = None
            st.error(str(error))

        if owner_df is not None:

            owner_records = []

            for _, owner_row in owner_df.iterrows():

                first_token = normalize_text(
                    owner_row[owner_first_col]
                )
                last_token = normalize_text(
                    owner_row[owner_last_col]
                )
                unit_name = clean_text(
                    owner_row[owner_unit_col]
                )

                if (
                    first_token == "" or last_token == ""
                    or unit_name == ""
                ):
                    continue

                display_name = (
                    f"{clean_text(owner_row[owner_first_col])} "
                    f"{clean_text(owner_row[owner_last_col])}"
                )

                owner_records.append((
                    first_token, last_token, display_name,
                    unit_name
                ))

            unknown_index = owner_match_df.loc[
                owner_match_df["Property"].eq("Unknown")
            ].index

            single_candidates = []
            multi_candidates = []

            for row_index in unknown_index:

                row = owner_match_df.loc[row_index]

                matched_field, matched_owners, candidate_units = (
                    find_owner_match_for_row(
                        row[owner_match_name_col],
                        row[owner_match_description_col],
                        owner_records
                    )
                )

                if not candidate_units:
                    continue

                entry = {
                    "index": row_index,
                    "matched_field": matched_field,
                    "matched_owners": matched_owners,
                    "candidate_units": candidate_units,
                }

                if len(candidate_units) == 1:
                    single_candidates.append(entry)
                else:
                    multi_candidates.append(entry)

            no_match_count = (
                len(unknown_index)
                - len(single_candidates)
                - len(multi_candidates)
            )

            s1, s2, s3, s4 = st.columns(4)
            s1.metric(
                "Unknown rows checked", f"{len(unknown_index):,}"
            )
            s2.metric(
                "Single-candidate matches",
                f"{len(single_candidates):,}"
            )
            s3.metric(
                "Multi-candidate matches",
                f"{len(multi_candidates):,}"
            )
            s4.metric("No match found", f"{no_match_count:,}")

            if not single_candidates and not multi_candidates:

                st.success(
                    "No name matches found in the remaining "
                    "Unknown rows — nothing to confirm here."
                )

            else:

                def owner_match_row_detail(row_index):
                    """
                    Full transaction-level context for one
                    Unknown row — same fields as the rest of the
                    tool's review tables (plus Amount), so a
                    match can be verified before it's confirmed.
                    """

                    return {
                        "Transaction date": owner_match_df.loc[
                            row_index,
                            results["transaction_date_column"]
                        ],
                        "Name": owner_match_df.loc[
                            row_index, owner_match_name_col
                        ],
                        "Num": owner_match_df.loc[
                            row_index, results["num_column"]
                        ],
                        "Class full name": owner_match_df.loc[
                            row_index,
                            results["class_full_name_column"]
                        ],
                        "Description": owner_match_df.loc[
                            row_index, owner_match_description_col
                        ],
                        "Amount": owner_match_df.loc[
                            row_index, results["amount_column"]
                        ],
                    }

                edited_single_df = None

                if single_candidates:

                    st.subheader(
                        "Single match — confirm to apply"
                    )
                    st.caption(
                        "Exactly one property came up. Still "
                        "your call."
                    )

                    if (
                        "owner_match_single_editor_version"
                        not in st.session_state
                    ):
                        st.session_state[
                            "owner_match_single_editor_version"
                        ] = 0

                    if st.button(
                        "Select all",
                        key="owner_match_select_all_button"
                    ):
                        st.session_state[
                            "owner_match_single_select_all"
                        ] = True
                        st.session_state[
                            "owner_match_single_editor_version"
                        ] += 1
                        st.rerun()

                    select_all_active = st.session_state.pop(
                        "owner_match_single_select_all", False
                    )

                    single_preview_df = pd.DataFrame(
                        [
                            {
                                **owner_match_row_detail(
                                    entry["index"]
                                ),
                                "Matched on": entry[
                                    "matched_field"
                                ],
                                "Matched Owner": ", ".join(
                                    entry["matched_owners"]
                                ),
                                "Proposed Property": entry[
                                    "candidate_units"
                                ][0],
                                "Confirm": select_all_active,
                            }
                            for entry in single_candidates
                        ],
                        index=[
                            entry["index"]
                            for entry in single_candidates
                        ]
                    )

                    single_editor_key = (
                        "owner_match_single_editor_"
                        + str(st.session_state[
                            "owner_match_single_editor_version"
                        ])
                    )

                    edited_single_df = st.data_editor(
                        single_preview_df,
                        column_config={
                            "Confirm": (
                                st.column_config.CheckboxColumn(
                                    default=False
                                )
                            )
                        },
                        disabled=[
                            "Transaction date", "Name", "Num",
                            "Class full name", "Description",
                            "Amount", "Matched on",
                            "Matched Owner", "Proposed Property"
                        ],
                        hide_index=True,
                        use_container_width=True,
                        key=single_editor_key
                    )

                edited_multi_groups = []

                if multi_candidates:

                    st.subheader(
                        "Multiple candidates — pick one"
                    )
                    st.caption(
                        "Grouped by which properties came up, so "
                        "every affected transaction is visible "
                        "together. Can't guess which — choose "
                        "the right Property per row, or leave it "
                        "Unknown."
                    )

                    multi_groups = {}

                    for entry in multi_candidates:
                        multi_groups.setdefault(
                            tuple(entry["candidate_units"]), []
                        ).append(entry)

                    for candidate_units, group_entries in (
                        multi_groups.items()
                    ):

                        owners_in_group = sorted(set(
                            owner
                            for group_entry in group_entries
                            for owner in group_entry[
                                "matched_owners"
                            ]
                        ))

                        st.markdown(
                            f"**{' or '.join(candidate_units)}**"
                            f" — via {', '.join(owners_in_group)}"
                            f" ({len(group_entries)} "
                            "transaction(s))"
                        )

                        group_preview_df = pd.DataFrame(
                            [
                                {
                                    **owner_match_row_detail(
                                        group_entry["index"]
                                    ),
                                    "Matched on": group_entry[
                                        "matched_field"
                                    ],
                                    "Matched Owner": ", ".join(
                                        group_entry[
                                            "matched_owners"
                                        ]
                                    ),
                                    "Property": (
                                        "— not confirmed —"
                                    ),
                                }
                                for group_entry in group_entries
                            ],
                            index=[
                                group_entry["index"]
                                for group_entry in group_entries
                            ]
                        )

                        group_key_suffix = "_".join(
                            unit.strip().lower().replace(" ", "-")
                            for unit in candidate_units
                        )

                        edited_group_df = st.data_editor(
                            group_preview_df,
                            column_config={
                                "Property": (
                                    st.column_config.SelectboxColumn(
                                        options=(
                                            ["— not confirmed —"]
                                            + list(candidate_units)
                                        )
                                    )
                                )
                            },
                            disabled=[
                                "Transaction date", "Name", "Num",
                                "Class full name", "Description",
                                "Amount", "Matched on",
                                "Matched Owner"
                            ],
                            hide_index=True,
                            use_container_width=True,
                            key=(
                                "owner_match_multi_editor_"
                                f"{group_key_suffix}"
                            )
                        )

                        edited_multi_groups.append(
                            (group_entries, edited_group_df)
                        )

                apply_clicked = st.button(
                    "Apply confirmed matches",
                    type="primary",
                    key="owner_match_apply_button"
                )

                if apply_clicked:

                    confirmed_single_index = []

                    if edited_single_df is not None:
                        confirmed_single_index = [
                            entry["index"]
                            for entry, confirmed in zip(
                                single_candidates,
                                edited_single_df["Confirm"].values
                            )
                            if confirmed
                        ]

                    for entry in single_candidates:
                        if entry["index"] in confirmed_single_index:
                            owner_match_df.loc[
                                entry["index"], "Property"
                            ] = entry["candidate_units"][0]

                    confirmed_multi = {}

                    for group_entries, edited_group_df in (
                        edited_multi_groups
                    ):
                        for group_entry, chosen in zip(
                            group_entries,
                            edited_group_df["Property"].values
                        ):
                            if chosen != "— not confirmed —":
                                confirmed_multi[
                                    group_entry["index"]
                                ] = chosen

                    for row_index, property_value in (
                        confirmed_multi.items()
                    ):
                        owner_match_df.loc[
                            row_index, "Property"
                        ] = property_value

                    st.session_state["owner_match_df"] = (
                        owner_match_df
                    )

                    resolved_count = (
                        len(confirmed_single_index)
                        + len(confirmed_multi)
                    )
                    st.success(
                        f"{resolved_count} row(s) resolved to a "
                        "Property. Everything else left as "
                        "Unknown."
                    )
                    st.rerun()

    # ========================================================
    # STEP 2 — ACCOUNT REMAPPING
    #
    # Adds two new columns — "Classification" and "Adjusted
    # Amount" — for rows belonging to accounts that mix income
    # and cost. "Account Name" and "Amount" are never modified.
    # See ACCOUNT_SPLIT_RULES for the account list and rules.
    #
    # Every rule is auto-applied the moment this step loads —
    # they're lookups, not decisions. The one exception is a
    # blank "Name" on Credit Card Clearing, which genuinely
    # needs a human call; that's the only thing you're ever
    # asked to do here.
    # ========================================================

    st.divider()
    st.header("🔀 Step 2 — Account Remapping")
    st.caption(
        "Split mixed accounts into their component parts — "
        "Income/Cost for Pass Thru accounts, Cost/Billback for "
        "Maintenance — without touching the original columns."
    )

    account_name_col = results["account_name_column"]
    transaction_date_col = results["transaction_date_column"]
    description_col = results["description_column"]
    amount_col = results["amount_column"]

    if "stage2_df" not in st.session_state:
        # Carries forward any rows Step 1B resolved by owner
        # name; falls back to Step 1's own output untouched when
        # Step 1B was skipped or never used.
        working_df = st.session_state.get(
            "owner_match_df", results["processed_df"]
        ).copy()
        working_df["Classification"] = ""
        working_df["Adjusted Amount"] = working_df[amount_col]
        st.session_state["stage2_df"] = working_df
        st.session_state["stage2_auto_applied"] = False

    stage2_df = st.session_state["stage2_df"]

    try:
        name_col = find_column(stage2_df, "Name")
        transaction_type_col = find_column(
            stage2_df, "Transaction Type"
        )
    except KeyError as error:
        name_col = None
        transaction_type_col = None
        st.error(str(error))

    if name_col and transaction_type_col and amount_col:

        # Runs once per stage2_df — every rule is a lookup, so
        # there's nothing to review before applying it. This
        # never overwrites a manual tag: once a row's
        # Classification is manually set, this pass isn't
        # re-run against it (guarded by stage2_auto_applied).
        if not st.session_state.get(
            "stage2_auto_applied", False
        ):

            for rule in ACCOUNT_SPLIT_RULES:

                account_mask = get_account_match_mask(
                    stage2_df, account_name_col,
                    rule["source_account"]
                )

                if not account_mask.any():
                    continue

                matched_index = stage2_df.loc[
                    account_mask
                ].index

                final_classification = stage2_df.loc[
                    account_mask
                ].apply(
                    lambda row, _rule=rule: classify_row_for_rule(
                        row, _rule, name_col,
                        transaction_type_col, amount_col
                    ),
                    axis=1
                )

                apply_rule_classification(
                    stage2_df, rule, matched_index,
                    final_classification, amount_col
                )

            st.session_state["stage2_df"] = stage2_df
            st.session_state["stage2_auto_applied"] = True

        account_summaries = []

        for rule in ACCOUNT_SPLIT_RULES:

            account_mask = get_account_match_mask(
                stage2_df, account_name_col,
                rule["source_account"]
            )
            matched_count = int(account_mask.sum())

            if matched_count == 0:
                continue

            classification_values = stage2_df.loc[
                account_mask, "Classification"
            ]
            blank_index = classification_values[
                classification_values.eq("")
            ].index

            account_summaries.append({
                "rule": rule,
                "matched_count": matched_count,
                "classified_count": (
                    matched_count - len(blank_index)
                ),
                "blank_index": blank_index,
            })

        total_matched = sum(
            summary["matched_count"]
            for summary in account_summaries
        )

        if total_matched == 0:

            st.info(
                "No transactions found for any of the "
                "configured accounts."
            )

        else:

            total_classified = sum(
                summary["classified_count"]
                for summary in account_summaries
            )

            manual_summary = next(
                (
                    summary for summary in account_summaries
                    if summary["rule"].get(
                        "allow_manual_tagging", False
                    )
                ),
                None
            )

            needs_input_count = (
                len(manual_summary["blank_index"])
                if manual_summary else 0
            )

            flagged_for_review_count = (
                total_matched
                - total_classified
                - needs_input_count
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                "Pass Thru rows matched", f"{total_matched:,}"
            )
            m2.metric(
                "Auto-classified", f"{total_classified:,}"
            )
            m3.metric("Needs your input", needs_input_count)
            m4.metric(
                "Flagged for review", flagged_for_review_count
            )

            if needs_input_count == 0 and (
                flagged_for_review_count == 0
            ):

                st.success(
                    "Every configured-account row is classified "
                    "— nothing needs review."
                )

            else:

                st.subheader("Needs review")

                if manual_summary and needs_input_count > 0:

                    manual_rule = manual_summary["rule"]
                    blank_index = manual_summary["blank_index"]

                    st.markdown(
                        f"**{manual_rule['source_account']}** "
                        f"— {needs_input_count} row(s) with a "
                        "blank Name. Tag each one as Income or "
                        "Cost:"
                    )

                    preview_columns = [
                        transaction_date_col,
                        name_col,
                        description_col,
                        amount_col,
                    ]

                    unresolved_editor_df = stage2_df.loc[
                        blank_index, preview_columns
                    ].copy()

                    unresolved_editor_df["Classification"] = ""

                    edited_df = st.data_editor(
                        unresolved_editor_df,
                        column_config={
                            "Classification": (
                                st.column_config.SelectboxColumn(
                                    options=["Income", "Cost"],
                                    required=True,
                                )
                            )
                        },
                        disabled=preview_columns,
                        hide_index=True,
                        use_container_width=True,
                        key="stage2_editor_manual"
                    )

                    all_tagged = all(
                        value in ("Income", "Cost")
                        for value in edited_df["Classification"]
                    )

                    apply_clicked = st.button(
                        "Apply tags — "
                        f"{manual_rule['source_account']}",
                        type="primary",
                        disabled=not all_tagged,
                        key="stage2_apply_manual"
                    )

                    if not all_tagged:
                        st.caption(
                            "Tag every row above before "
                            "applying."
                        )

                    if apply_clicked:

                        final_classification = pd.Series(
                            edited_df["Classification"].values,
                            index=blank_index
                        )

                        working_df = stage2_df.copy()

                        (
                            parseable_cost_index,
                            income_index,
                            unparseable_cost_index
                        ) = apply_rule_classification(
                            working_df, manual_rule, blank_index,
                            final_classification, amount_col
                        )

                        st.session_state["stage2_df"] = (
                            working_df
                        )

                        st.success(
                            f"Classified "
                            f"{len(parseable_cost_index)} "
                            "row(s) as "
                            f"'{manual_rule['cost_label']}' and "
                            f"{len(income_index)} row(s) as "
                            f"'{manual_rule['income_label']}'."
                        )

                        if len(unparseable_cost_index) > 0:
                            st.warning(
                                f"{len(unparseable_cost_index)} "
                                "row(s) could not be classified "
                                "because their Amount could not "
                                "be parsed."
                            )

                        st.rerun()

                if flagged_for_review_count > 0:

                    st.markdown(
                        "**Flagged for review** — Transaction "
                        "Type not covered by the mapping "
                        "(nothing was guessed):"
                    )

                    review_frames = []

                    for summary in account_summaries:

                        rule = summary["rule"]

                        if rule.get(
                            "allow_manual_tagging", False
                        ):
                            continue

                        if len(summary["blank_index"]) == 0:
                            continue

                        review_frames.append(
                            stage2_df.loc[
                                summary["blank_index"],
                                [
                                    transaction_date_col,
                                    account_name_col,
                                    transaction_type_col,
                                    name_col,
                                    amount_col,
                                ]
                            ]
                        )

                    review_df = pd.concat(review_frames)

                    st.dataframe(
                        review_df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(
                            420, 60 + 35 * len(review_df)
                        )
                    )

            with st.expander(
                "Per-account detail "
                f"({len(account_summaries)} accounts)"
            ):
                for summary in account_summaries:

                    rule = summary["rule"]
                    blank_count = len(summary["blank_index"])
                    status_icon = (
                        "⚠️" if blank_count > 0 else "✅"
                    )

                    st.markdown(
                        f"{status_icon} "
                        f"**{rule['source_account']}** — "
                        f"{summary['classified_count']}/"
                        f"{summary['matched_count']} classified"
                        f" → `{rule['income_label']}` / "
                        f"`{rule['cost_label']}`"
                    )

    stage2_df = st.session_state["stage2_df"]

    st.subheader("Step 2 output")
    st.dataframe(
        stage2_df,
        use_container_width=True,
        height=380
    )

    stage2_output_filename = results["output_filename"].replace(
        "_mapped.csv", "_remapped.csv"
    )

    st.download_button(
        "⬇️ Download remapped CSV",
        data=stage2_df.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name=stage2_output_filename,
        mime="text/csv"
    )

    # ========================================================
    # STEP 3 — SOFTWARE ACCOUNT VENDOR REMAPPING
    #
    # Every row coded to the "Software" account is remapped:
    #   - Name contains a Revenue Management match term
    #     (case-insensitive substring) -> Revenue Management
    #   - everything else, blank Name included -> Software - Other
    #
    # Only the short Revenue Management list is maintained; the
    # growing tail of software vendors is swept into
    # Software - Other. Nothing is left as bare "Software". Both
    # the match terms and the two account names are editable.
    # ========================================================

    st.divider()
    st.header("🏷️ Step 3 — Software Account Vendor Remapping")
    st.caption(
        "Every Software-account row is remapped: vendors matching "
        "a Revenue Management term go to that account, everything "
        "else goes to Software - Other."
    )

    SOFTWARE_TERM_COLUMN = (
        "Revenue Management match term (Name contains, "
        "case-insensitive)"
    )

    if "stage3_revmgmt_terms" not in st.session_state:
        st.session_state["stage3_revmgmt_terms"] = pd.DataFrame(
            {
                SOFTWARE_TERM_COLUMN: list(
                    DEFAULT_SOFTWARE_REVENUE_MANAGEMENT_TERMS
                )
            }
        )

    account_name_cols = st.columns(2)

    with account_name_cols[0]:
        revmgmt_account_name = st.text_input(
            "Revenue Management account name",
            value=SOFTWARE_REVENUE_MANAGEMENT_ACCOUNT,
            key="stage3_revmgmt_account"
        )

    with account_name_cols[1]:
        other_account_name = st.text_input(
            "Other account name (everything else in Software)",
            value=SOFTWARE_OTHER_ACCOUNT,
            key="stage3_other_account"
        )

    revmgmt_account_name = (
        clean_text(revmgmt_account_name)
        or SOFTWARE_REVENUE_MANAGEMENT_ACCOUNT
    )
    other_account_name = (
        clean_text(other_account_name) or SOFTWARE_OTHER_ACCOUNT
    )

    st.markdown(
        "**Revenue Management vendors** — a Software row whose "
        "Name contains any term below is remapped to the Revenue "
        "Management account. Add or remove rows as needed:"
    )

    revmgmt_terms_editor_df = st.data_editor(
        st.session_state["stage3_revmgmt_terms"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="stage3_revmgmt_terms_editor"
    )

    st.session_state["stage3_revmgmt_terms"] = (
        revmgmt_terms_editor_df
    )

    revenue_management_terms = [
        normalize_text(term)
        for term in revmgmt_terms_editor_df[
            SOFTWARE_TERM_COLUMN
        ].tolist()
        if normalize_text(term) != ""
    ]

    stage3_df = stage2_df.copy()

    software_mask = get_account_match_mask(
        stage3_df,
        account_name_col,
        SOFTWARE_SOURCE_ACCOUNT
    )

    software_index = stage3_df.loc[software_mask].index

    if len(software_index) == 0:

        st.info(
            "No rows are currently coded to the Software "
            "account."
        )

    else:

        vendor_values = (
            stage3_df.loc[software_index, name_col]
            .map(clean_text)
        )

        normalized_vendor_values = vendor_values.map(
            normalize_text
        )

        def is_revenue_management_vendor(vendor_key):
            return any(
                term in vendor_key
                for term in revenue_management_terms
            )

        revmgmt_row_mask = normalized_vendor_values.map(
            is_revenue_management_vendor
        )

        revmgmt_index = revmgmt_row_mask[revmgmt_row_mask].index
        other_index = revmgmt_row_mask[~revmgmt_row_mask].index

        stage3_df.loc[revmgmt_index, account_name_col] = (
            revmgmt_account_name
        )
        stage3_df.loc[other_index, account_name_col] = (
            other_account_name
        )

        metric_cols = st.columns(2)
        metric_cols[0].metric(
            f"→ {revmgmt_account_name}", f"{len(revmgmt_index):,}"
        )
        metric_cols[1].metric(
            f"→ {other_account_name}", f"{len(other_index):,}"
        )

        def vendor_breakdown(index):
            return (
                vendor_values.loc[index]
                .replace("", "(blank vendor)")
                .value_counts()
                .rename_axis("Vendor (Name)")
                .reset_index(name="Rows")
            )

        st.markdown(
            f"**Swept into {other_account_name}** — check for any "
            "vendor that should be Revenue Management:"
        )
        other_breakdown_df = vendor_breakdown(other_index)
        st.dataframe(
            other_breakdown_df,
            use_container_width=True,
            hide_index=True,
            height=min(360, 60 + 35 * len(other_breakdown_df))
        )

        if len(revmgmt_index) > 0:
            st.markdown(
                f"**Mapped to {revmgmt_account_name}:**"
            )
            revmgmt_breakdown_df = vendor_breakdown(revmgmt_index)
            st.dataframe(
                revmgmt_breakdown_df,
                use_container_width=True,
                hide_index=True,
                height=min(
                    240, 60 + 35 * len(revmgmt_breakdown_df)
                )
            )

    st.session_state["stage3_df"] = stage3_df

    st.subheader("Step 3 output")
    st.dataframe(
        stage3_df,
        use_container_width=True,
        height=380
    )

    stage3_output_filename = results["output_filename"].replace(
        "_mapped.csv", "_remapped_v2.csv"
    )

    st.download_button(
        "⬇️ Download Step 3 CSV",
        data=stage3_df.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name=stage3_output_filename,
        mime="text/csv"
    )

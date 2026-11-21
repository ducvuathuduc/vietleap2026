"""FiinQuant screening: VND -> bn, one indicator per call, composed movements, gates and the PDF audit."""

import pandas as pd

from vlkit.npl.ingest import fiin_screening as screen
from vlkit.npl.ingest.extra_landing import write_silver

NAME = screen.INDICATORS


def reply(**values):
    """A StockScreening reply: the ticker column plus one column per indicator, in VND."""
    columns = {screen.TICKER: list(values.pop("banks"))}
    for field, amounts in values.items():
        columns[NAME[field]] = amounts
    return pd.DataFrame(columns)


class Screening:
    def __init__(self, frames):
        self.frames = frames
        self.requests = []

    def get(self, filter):
        self.requests.append(filter)
        name = filter[0]["indicatorName"]
        interim = filter[0]["indicatorInterimId"]
        return self.frames.get((name, interim), pd.DataFrame())


class Client:
    def __init__(self, frames):
        self.frames = frames
        self.screening = Screening(frames)

    def StockScreening(self):
        return self.screening


class Collector:
    """The parts of the real Collector that run_screening uses, without bronze or a login."""

    def __init__(self, frames):
        self.client = Client(frames)
        self.calls = []
        self.frames = frames

    def login(self):
        return self

    def call(self, dataset, params, operation, doc_url=""):
        frame = pd.DataFrame(operation())
        self.calls.append({"dataset": dataset, "params": params, "raw_sha256": f"sha{len(self.calls)}"})
        return frame


def test_values_are_vnd_divided_by_a_billion_and_keyed_by_ticker():
    frame = reply(banks=["VCB", "TCB"], group_2_watch=[12_345_600_000.0, 7_000_000_000.0])
    assert screen.values_of(frame, NAME["group_2_watch"]) == {"VCB": 12.3456, "TCB": 7.0}
    assert screen.values_of(pd.DataFrame(), "x") == {}


def test_each_call_asks_for_one_indicator_and_the_note_interim():
    collector = Collector({(NAME["group_2_watch"], "Q1-2025"): reply(banks=["VCB"], group_2_watch=[1e9])})
    rows = screen.collect(collector, ["group_2_watch"], ["2025Q1"], banks={"VCB"})
    request = collector.client.screening.requests[0][0]
    assert request["indicatorName"] == NAME["group_2_watch"]
    assert request["interimCode"] == "Quarterly" and request["indicatorInterimId"] == "Q1-2025"
    assert rows == [{"bank": "VCB", "period": "2025Q1", "field": "group_2_watch", "value_vnd_bn": 1.0,
                     "raw_sha256": "sha0"}]


def test_the_movement_total_is_the_sum_of_its_general_and_specific_parts():
    rows = [{"bank": "VCB", "period": "2025Q2", "field": field, "value_vnd_bn": value, "raw_sha256": "s"}
            for field, value in [("provision_opening_general", 1.0), ("provision_opening_specific", 2.0),
                                 ("provision_charge_general", 3.0), ("provision_charge_specific", 4.0),
                                 ("provision_used_general", 5.0), ("provision_used_specific", 6.0),
                                 ("provision_total", 100.0)]]
    composed = {row["field"]: row["value_vnd_bn"] for row in screen.compose(rows)}
    assert composed["provision_opening"] == 3.0 and composed["provision_charge"] == 7.0
    assert composed["provision_used_writeoff"] == 11.0 and composed["provision_closing"] == 100.0


def test_a_year_to_date_flow_gets_a_single_quarter_row_and_a_balance_does_not():
    rows = [{"bank": "VCB", "period": period, "field": "provision_charge", "value_vnd_bn": value, "raw_sha256": "s"}
            for period, value in [("2025Q1", 5.0), ("2025Q2", 12.0)]]
    frame = screen.to_silver(rows, basis="ytd")
    quarterly = {(row.period, row.basis): row.value_vnd_bn for row in frame.itertuples()}
    assert quarterly[("2025Q2", "quarterly")] == 7.0 and quarterly[("2025Q1", "quarterly")] == 5.0
    assert quarterly[("2025Q2", "ytd")] == 12.0
    balances = screen.to_silver([{"bank": "VCB", "period": "2025Q2", "field": "loans_customer",
                                  "value_vnd_bn": 9.0, "raw_sha256": "s"}], basis="ytd")
    assert list(balances["basis"]) == ["point"] and balances.iloc[0]["unit"] == "bn"


def test_flow_basis_compares_the_annual_total_and_never_subtracts_another_bank():
    rows = []
    for bank, values in {"VCB": [2., 6., 9., 12., 12.], "BID": [7., 11., 13., 17., 48.]}.items():
        rows.extend({"bank": bank, "period": period, "field": "provision_used_specific",
                     "value_vnd_bn": value, "raw_sha256": bank + period}
                    for period, value in zip(["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2025FY"], values))
    basis, _ = screen.flow_basis(rows)
    assert basis[("VCB", "2025", "provision_used_specific")] == "ytd"
    assert basis[("BID", "2025", "provision_used_specific")] == "quarter"
    silver = screen.to_silver(rows, basis=basis)
    q2 = silver[silver.period.eq("2025Q2") & silver.basis.eq("quarterly")].set_index("bank")
    assert q2.value_vnd_bn.to_dict() == {"BID": 11., "VCB": 4.}
    assert not silver.period.str.endswith("FY").any()


def test_contiguous_zeros_are_zero_quarter_flows_under_either_basis():
    rows = [{"bank": "VCB", "period": period, "field": "provision_used_general",
             "value_vnd_bn": 0., "raw_sha256": period}
            for period in ["2025Q1", "2025Q2", "2025Q4"]]
    silver = screen.to_silver(rows, basis={})
    quarter = silver.loc[silver.basis.eq("quarterly")].set_index("period")
    assert quarter.value_vnd_bn.to_dict() == {"2025Q1": 0., "2025Q2": 0.}


def test_no_flow_convention_is_inferred_when_both_disagree_with_the_yearly_value():
    samples = {"2024Q1": 2, "2024Q2": 4, "2024Q3": 6, "2024Q4": 8, "2024FY": 20,
               "2025Q1": 2, "2025Q2": 4, "2025Q3": 6, "2025Q4": 8, "2025FY": 100}
    rows = [{"bank": "BID", "period": period, "field": "provision_used_specific",
             "value_vnd_bn": value, "raw_sha256": period} for period, value in samples.items()]
    basis, _ = screen.flow_basis(rows)
    assert basis[("BID", "2024", "provision_used_specific")] == "quarter"
    assert basis[("BID", "2025", "provision_used_specific")] == "unknown"


def test_the_audit_reports_the_share_of_overlapping_values_that_match():
    def row(bank, field, value, reader="fiinquant_screening"):
        return {"bank": bank, "period": "2025Q2", "field": field, "basis": "point", "value_vnd_bn": value,
                "page": 1, "source_url": "https://x.test/a.pdf", "statement_type": "consolidated", "unit": "bn",
                "reader": reader, "grade": "single", "raw_sha256": "s"}
    screening = pd.DataFrame([row("VCB", "loans_customer", 1000.0), row("VCB", "group_2_watch", 10.0)])
    pdf = pd.DataFrame([row("VCB", "loans_customer", 1000.5), row("VCB", "group_2_watch", 20.0)])
    audit, _ = screen.audit(screening, pdf)
    assert audit["pairs"] == 2 and audit["match"] == 1 and audit["rate"] == 0.5
    assert audit["by_field"]["loans_customer"]["rate"] == 1.0


def test_the_audit_headline_is_the_comparable_match_and_keeps_every_overlap():
    def row(field, value, grade="single", scope="consolidated", reader="fiinquant_screening"):
        return {"bank": "VCB", "period": "2025Q2", "field": field, "basis": "point", "value_vnd_bn": value,
                "page": 1, "source_url": "https://x.test/a.pdf", "statement_type": scope, "unit": "bn",
                "reader": reader, "grade": grade, "raw_sha256": "s"}
    screening = pd.DataFrame([
        row("loans_customer", 1000.0), row("group_2_watch", 10.0), row("group_5_loss", 5.0),
    ])
    pdf = pd.DataFrame([
        row("loans_customer", 1000.5), row("group_2_watch", 20.0),
        row("group_5_loss", 5.0, grade="contested"),
    ])
    audit, _ = screen.audit(screening, pdf)
    assert audit["headline"] == {"matched": 1, "comparable": 2, "rate": 0.5}
    assert audit["all_rows"] == {"matched": 2, "rows": 3, "rate": 2 / 3}


def test_run_screening_writes_gated_silver_and_quarantines_the_bank_that_fails(tmp_path):
    write_silver(tmp_path, "bank_quarter.parquet", pd.DataFrame([
        {"ticker": "VCB", "period": "2025Q1", "npl": 0.05}, {"ticker": "TCB", "period": "2025Q1", "npl": 0.05}]))
    fields = ["group_1_current", "group_2_watch", "group_3_substandard", "group_4_doubtful", "group_5_loss",
              "loans_customer", "provision_total"]
    frames = {}
    # VCB: groups 900+50+20+20+10 = 1000 = loans (5% npl, as the vendor prints it). TCB: 1000 groups vs 1100 loans.
    frames[(NAME["group_1_current"], "Q1-2025")] = reply(banks=["VCB", "TCB"], group_1_current=[900e9, 900e9])
    for field, amount in (("group_2_watch", 50e9), ("group_3_substandard", 20e9), ("group_4_doubtful", 20e9),
                          ("group_5_loss", 10e9)):
        frames[(NAME[field], "Q1-2025")] = reply(banks=["VCB", "TCB"], **{field: [amount, amount]})
    frames[(NAME["loans_customer"], "Q1-2025")] = reply(banks=["VCB", "TCB"], loans_customer=[1000e9, 1100e9])
    frames[(NAME["provision_total"], "Q1-2025")] = reply(banks=["VCB", "TCB"], provision_total=[30e9, 33e9])
    log = screen.run_screening(lake=tmp_path, collector=Collector(frames), fields=fields, periods=["2025Q1"])
    silver = pd.read_parquet(tmp_path / "silver" / screen.SCREEN)
    quarantine = pd.read_parquet(tmp_path / "silver" / screen.QUARANTINE)
    assert log["rows"] > 0 and log["basis_evidence"] == {}
    assert set(silver["bank"]) == {"VCB"}                    # TCB's groups sum 1000 against 1100 of loans: -9%
    assert set(quarantine["bank"]) == {"TCB"}
    assert quarantine["reason"].str.contains("groups_sum_to_loans").all()
    gates = pd.read_csv(tmp_path / "silver" / screen.GATES)
    assert "groups_sum_to_loans" in set(gates["gate"])
    assert set(silver["reader"]) == {"fiinquant_screening"} and set(silver["unit"]) == {"bn"}
    assert set(silver["basis"]) == {"fiinquant_screening"} and set(silver["flow_basis"]) == {"point"}
    assert log["coverage"]["group_2_watch"]["2025Q1"] == 2

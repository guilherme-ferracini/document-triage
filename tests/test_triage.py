from decimal import Decimal
from pathlib import Path

from triage.classify import MANUAL, rule_classifier, triage_folder, triage_text
from triage.fields import cnpj_is_valid, largest_amount
from triage.llm import LLMClient

INBOX = Path(__file__).parents[1] / "samples" / "inbox"
MOCK = LLMClient("mock", mock_fn=rule_classifier)
RESULTS = {r.file: r for r in triage_folder(INBOX, MOCK)}


def test_cnpj_check_digits():
    assert cnpj_is_valid("11.222.333/0001-81")
    assert not cnpj_is_valid("11.222.333/0001-82")
    assert not cnpj_is_valid("11.111.111/1111-11")


def test_amount_parsing():
    assert largest_amount("Total R$ 1.234,56 and R$ 99,00") == Decimal("1234.56")


def test_expected_routing():
    expected = {
        "01_nfse_bussola_4512.txt": "Tax",
        "02_danfe_aurora_88127.txt": "Tax",
        "03_extrato_outubro.txt": "Accounting",
        "04_holerite_maria.txt": "Payroll",
        "05_das_setembro.txt": "Tax",
        "06_contrato_prestacao.txt": "Legal",
        "07_plano_saude_out.txt": "Payroll",
        "08_bilhete_cliente.txt": MANUAL,
    }
    assert {k: v.team for k, v in RESULTS.items()} == expected


def test_invalid_cnpj_is_flagged():
    assert any("Invalid CNPJ" in w for w in RESULTS["07_plano_saude_out.txt"].warnings)


def test_low_confidence_goes_to_manual_review():
    assert RESULTS["08_bilhete_cliente.txt"].team == MANUAL


def test_unparseable_model_output_is_safe():
    bad = LLMClient("mock", mock_fn=lambda s, p: "I think it is an invoice")
    assert triage_text("x.txt", "anything", bad).team == MANUAL

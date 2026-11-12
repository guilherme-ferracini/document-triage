"""Classifies incoming client documents and routes them to the right team.

Demo mode uses weighted keyword rules; with an API key an LLM classifies with a
confidence score. In both cases low confidence goes to a manual-review queue
instead of a team, so nothing is misrouted silently."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .fields import cnpj_is_valid, cnpjs, first_date, largest_amount
from .llm import LLMClient

CATEGORIES: Dict[str, Dict] = {
    "invoice": {"team": "Tax", "keywords": {"nota fiscal": 3, "nf-e": 3, "nfs-e": 3, "danfe": 3, "chave de acesso": 2,
                                            "prestador": 1, "tomador": 1, "valor total da nota": 2}},
    "bank_statement": {"team": "Accounting", "keywords": {"extrato": 3, "saldo anterior": 2, "saldo final": 2,
                                                          "agencia": 1, "conta corrente": 2, "pix": 1}},
    "payslip": {"team": "Payroll", "keywords": {"holerite": 3, "recibo de pagamento de salario": 3, "proventos": 2,
                                                "descontos": 1, "salario base": 2, "fgts do mes": 2}},
    "tax_payment_slip": {"team": "Tax", "keywords": {"documento de arrecadacao": 3, "darf": 3, "das": 2,
                                                     "codigo de barras": 1, "periodo de apuracao": 2, "vencimento": 1}},
    "contract": {"team": "Legal", "keywords": {"contrato": 3, "clausula": 2, "contratante": 2, "contratada": 2,
                                               "foro": 1, "vigencia": 1}},
    "health_plan_invoice": {"team": "Payroll", "keywords": {"plano de saude": 3, "beneficiario": 2, "coparticipacao": 2,
                                                            "operadora": 2, "mensalidade": 1}},
}
MANUAL = "Manual review"
MIN_CONFIDENCE = 0.6


@dataclass
class Triage:
    file: str
    category: str
    team: str
    confidence: float
    fields: Dict[str, Optional[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def rule_scores(text: str) -> Dict[str, int]:
    t = _norm(text)
    return {cat: sum(w for kw, w in spec["keywords"].items() if re.search(rf"\b{re.escape(kw)}\b", t))
            for cat, spec in CATEGORIES.items()}


def rule_classifier(_system: str, prompt: str) -> str:
    """Demo-mode 'model': keyword scores turned into a category and a confidence."""
    text = prompt.split("DOCUMENT:", 1)[1]
    scores = rule_scores(text)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    (best, s1), (_, s2) = ranked[0], ranked[1]
    confidence = 0.0 if s1 == 0 else round(min(1.0, s1 / 6) * (1 - s2 / (s1 + s2 + 1e-9) / 2), 2)
    return json.dumps({"category": best if s1 else "unknown", "confidence": confidence})


SYSTEM = ("You classify documents that clients send to a Brazilian accounting firm. Categories: "
          + ", ".join(CATEGORIES) + ", unknown. Reply ONLY with JSON: "
          "{\"category\": \"...\", \"confidence\": 0.0-1.0}. Use a low confidence when unsure.")


def triage_text(name: str, text: str, client: LLMClient) -> Triage:
    raw = client.complete(SYSTEM, "DOCUMENT:\n" + text[:6000], max_tokens=200)
    try:
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        category, confidence = data.get("category", "unknown"), float(data.get("confidence", 0))
    except (ValueError, TypeError):
        category, confidence = "unknown", 0.0

    team = CATEGORIES.get(category, {}).get("team", MANUAL)
    warnings = []
    if confidence < MIN_CONFIDENCE:
        warnings.append(f"Low confidence ({confidence:.2f}): sent to manual review.")
        team = MANUAL

    found = cnpjs(text)
    invalid = [c for c in found if not cnpj_is_valid(c)]
    if invalid:
        warnings.append("Invalid CNPJ check digits: " + ", ".join(invalid))
    d, amount = first_date(text), largest_amount(text)
    return Triage(
        file=name, category=category, team=team, confidence=confidence,
        fields={"cnpj": found[0] if found else None, "date": d.isoformat() if d else None,
                "amount": str(amount) if amount is not None else None},
        warnings=warnings,
    )


def triage_folder(folder: Path, client: LLMClient) -> List[Triage]:
    return [triage_text(p.name, p.read_text(encoding="utf-8"), client) for p in sorted(folder.glob("*.txt"))]

# Document Triage

[![tests](https://github.com/guilherme-ferracini/document-triage/actions/workflows/tests.yml/badge.svg)](https://github.com/guilherme-ferracini/document-triage/actions)

Classifies the documents clients send to an accounting firm (invoices, bank statements, payslips, tax payment slips, contracts, health-plan invoices), **routes each one to the right team**, extracts key fields and **validates CNPJ check digits**. Anything the classifier is not sure about goes to a **manual-review queue** instead of the wrong desk.

## Why this exists

In an accounting firm, documents arrive mixed together, through e-mail, WhatsApp and portals. Someone has to open each file, decide whether it belongs to Tax, Payroll or Accounting, and forward it. I'm building a client portal for document exchange and submission. This repo is a clean, standalone version of the triage step, using fictional documents.

Design choices:

- **Confidence decides the route.** Below the confidence threshold (default 0.6), the document goes to "Manual review". A slow correct route beats a fast wrong one.
- **Validation in code.** CNPJ check digits, dates and amounts are extracted and checked deterministically. The LLM classifies; it does not validate.
- **Safe failure.** If the model returns something that is not valid JSON, the document is routed to manual review. It is never dropped.
- **Two classifiers, one interface.** Weighted keyword rules (demo mode, free, explainable) or an LLM (Claude/OpenAI) for messy real-world documents.

## Quickstart

```bash
pip install -r requirements.txt

# Demo mode: keyword rules, no API key needed
python -m triage samples/inbox --out out/routing.csv

# LLM classification
export LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=...      # or openai
python -m triage samples/inbox
```

```
01_nfse_bussola_4512.txt   invoice              -> Tax            conf 1.00  CNPJ 11.222.333/0001-81  R$ 15300.00
03_extrato_outubro.txt     bank_statement       -> Accounting     conf 1.00  CNPJ 77.888.999/0001-81  R$ 82410.33
04_holerite_maria.txt      payslip              -> Payroll        conf 1.00  CNPJ 77.888.999/0001-81  R$ 4800.00
07_plano_saude_out.txt     health_plan_invoice  -> Payroll        conf 0.92  CNPJ 98.765.432/0001-99  R$ 19732.50
                           ! Invalid CNPJ check digits: 98.765.432/0001-99
08_bilhete_cliente.txt     unknown              -> Manual review  conf 0.00
Queue sizes: Tax: 3, Payroll: 2, Accounting: 1, Legal: 1, Manual review: 1
```

Full output: [`samples/sample_output/routing.csv`](samples/sample_output/routing.csv)

## Categories and teams

| Category | Team |
|---|---|
| invoice (NF-e / NFS-e) | Tax |
| tax_payment_slip (DAS / DARF) | Tax |
| bank_statement | Accounting |
| payslip | Payroll |
| health_plan_invoice | Payroll |
| contract | Legal |
| unknown or low confidence | Manual review |

Categories, keywords and teams live in one dictionary in `triage/classify.py`.

## Notes

- Sample documents are plain text to keep the demo dependency-free. In production, PDFs and images go through text extraction/OCR first (see [pdf-to-erp-extractor](https://github.com/guilherme-ferracini/pdf-to-erp-extractor)).
- All companies, people and CNPJs are fictional.

## License

MIT

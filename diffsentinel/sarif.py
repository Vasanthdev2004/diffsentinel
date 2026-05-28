from __future__ import annotations

import json
from typing import Any


def report_to_sarif(report: dict[str, Any]) -> dict[str, Any]:
    rules = {}
    results = []
    for issue in report.get("issues", []):
        rule_id = str(issue["category"])
        rules.setdefault(
            rule_id,
            {
                "id": rule_id,
                "name": rule_id.replace("_", " ").title(),
                "shortDescription": {"text": rule_id},
                "fullDescription": {"text": str(issue.get("explanation", ""))},
                "help": {"text": str(issue.get("impact", ""))},
            },
        )
        level = "error" if issue.get("severity") == "CRITICAL" else "warning"
        results.append(
            {
                "ruleId": rule_id,
                "level": level,
                "message": {"text": f"{issue.get('explanation')} Impact: {issue.get('impact')}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": str(issue.get("file_path"))},
                            "region": {"startLine": int(issue.get("line_number", 1))},
                        }
                    }
                ],
                "properties": {
                    "severity": issue.get("severity"),
                    "confidence": issue.get("confidence"),
                    "auto_applyable": issue.get("auto_applyable"),
                    "optimized_code": issue.get("optimized_code"),
                    "diffsentinel_id": issue.get("id"),
                },
            }
        )

    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "DiffSentinel",
                        "informationUri": "https://github.com/Vasanthdev2004/diffsentinel",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def sarif_json(report: dict[str, Any]) -> str:
    return json.dumps(report_to_sarif(report), indent=2)

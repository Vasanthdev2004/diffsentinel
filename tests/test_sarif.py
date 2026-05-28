from diffsentinel.sarif import report_to_sarif


def test_report_to_sarif_maps_critical_issue():
    report = {
        "issues": [
            {
                "id": "handler.py:5:BLOCKING_IO",
                "file_path": "handler.py",
                "line_number": 5,
                "severity": "CRITICAL",
                "category": "BLOCKING_IO",
                "explanation": "Blocking sleep is running inside an async function.",
                "impact": "Blocks the event loop.",
                "confidence": 0.98,
                "auto_applyable": True,
                "optimized_code": "    await asyncio.sleep(1)",
            }
        ]
    }

    sarif = report_to_sarif(report)
    result = sarif["runs"][0]["results"][0]

    assert sarif["version"] == "2.1.0"
    assert result["ruleId"] == "BLOCKING_IO"
    assert result["level"] == "error"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "handler.py"
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 5

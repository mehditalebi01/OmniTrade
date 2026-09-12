import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
UML = ROOT / "modeling" / "visual-paradigm" / "plantuml"


def ids(prefix: str, text: str) -> set[str]:
    return set(re.findall(rf"\b{prefix}-\d{{2}}\b", text))


def expected(prefix: str, count: int) -> set[str]:
    return {f"{prefix}-{number:02d}" for number in range(1, count + 1)}


def test_nfr_08_requirement_catalog_has_unique_complete_stable_ids() -> None:
    requirements = (DOCS / "requirements.md").read_text(encoding="utf-8")

    assert ids("UR", requirements) == expected("UR", 12)
    assert ids("FR", requirements) == expected("FR", 38)
    assert ids("NFR", requirements) == expected("NFR", 10)

    table_ids = re.findall(r"^\| ((?:UR|FR|NFR)-\d{2}) \|", requirements, re.MULTILINE)
    assert len(table_ids) == len(set(table_ids)) == 60


def test_nfr_08_traceability_covers_every_requirement_and_custom_algorithm() -> None:
    traceability = (DOCS / "traceability.md").read_text(encoding="utf-8")

    assert expected("UR", 12) <= ids("UR", traceability)
    assert expected("FR", 38) <= ids("FR", traceability)
    assert expected("NFR", 10) <= ids("NFR", traceability)
    assert expected("CCL", 8) <= ids("CCL", traceability)


def test_nfr_08_complex_logic_has_code_test_trace_and_no_model_complexity_claim() -> None:
    content = (DOCS / "complex-custom-logic.md").read_text(encoding="utf-8")

    assert ids("CCL", content) == expected("CCL", 8)
    for marker in ("Implementation:", "Trace:", "Verification/UML:", "Complexity:"):
        assert content.count(marker) >= 6
    assert "pretrained language models" in content
    assert "not classified as complex custom logic" in content


def test_nfr_08_v7_diagrams_use_the_expected_uml_notation() -> None:
    expected_notation = {
        "V7_00_Use_Case.puml": ("actor ", "usecase "),
        "V7_01_XP_TDD_Activity.puml": ("start", "if (", "stop"),
        "V7_02_Component.puml": ("component ", "<<IUserAPI>>"),
        "V7_03_Package.puml": ("package ",),
        "V7_04_Class.puml": ("class ", '"1" *--'),
        "V7_05_Validator_Activity.puml": ("start", "fork", "stop"),
        "V7_06_Scheduler_Activity.puml": ("repeat", "fork", "stop"),
        "V7_07_Evidence_Sequence.puml": ("participant ", "loop ", "alt "),
        "V7_08_Failure_Activity.puml": ("start", "elseif", "stop"),
        "V7_09_Research_Risk_Activity.puml": ("repeat", "fork", "stop"),
        "V7_10_Lineage_Sequence.puml": ("participant ", "loop ", "par "),
        "V7_11_Run_State.puml": ("[*] -->", "Paused --> Queued"),
        "V7_12_Deployment.puml": ("node ", "artifact ", "cloud "),
        "V7_13_Object.puml": ("object ", ":Run"),
        "V7_14_Composite.puml": ('component "runtime:WorkflowRuntime"', "portin "),
        "V7_15_Timing.puml": ("robust ", "@120"),
        "V7_16_Communication.puml": ("object ", "1.1:"),
        "V7_17_End_To_End_Sequence.puml": ("actor ", "participant ", "loop "),
    }

    for name, markers in expected_notation.items():
        source = (UML / name).read_text(encoding="utf-8")
        assert source.startswith("@startuml") and source.rstrip().endswith("@enduml")
        assert all(marker in source for marker in markers), name

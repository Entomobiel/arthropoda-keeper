"""De voorbeeld-caresheets in de repository moeten geldig blijven."""

from pathlib import Path

from arthropoda_core.caresheet import parse_caresheets

EXAMPLES = Path(__file__).resolve().parents[2] / "caresheets" / "voorbeelden.yaml"


def test_example_caresheets_are_valid():
    sheets = parse_caresheets(EXAMPLES.read_text(encoding="utf-8"))
    names = [s.species["scientific_name"] for s in sheets]
    assert "Lasius niger" in names and "Messor barbarus" in names
    messor = next(s for s in sheets if s.species["scientific_name"] == "Messor barbarus")
    assert messor.species["ant"]["type"] == "harvester"

import sys
from pathlib import Path

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_import_package():
    """Test that the main package imports correctly."""
    import swift_app
    assert swift_app is not None


def test_cli_parser():
    """Test CLI parser builds successfully."""
    from swift_app.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["-b", "krishna", "-q"])

    assert args.basin == "krishna"
    assert args.q is True


def test_dataset_mapping():
    """Ensure dataset mapping exists."""
    from swift_app.cli import DATASETS

    assert "q" in DATASETS
    assert "rf" in DATASETS
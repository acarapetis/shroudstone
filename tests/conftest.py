from pathlib import Path
from typing import NamedTuple

import pytest

data_dir = Path(__file__).parent / "replays"


def pytest_addoption(parser):
    parser.addoption("--update-golden", default=False, action="store_true")


class ReplayCase(NamedTuple):
    replay_file: Path
    summary_file: Path
    expected_name_file: Path


@pytest.fixture(params=list(data_dir.glob("**/*.SGReplay")), ids=lambda c: c.stem)
def replay_case(request):
    path = request.param
    yield ReplayCase(
        replay_file=path,
        summary_file=path.with_suffix(".json"),
        expected_name_file=path.with_suffix(".txt"),
    )

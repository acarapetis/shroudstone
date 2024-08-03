import json

from shroudstone.replay import summarize_replay
from tests.conftest import ReplayCase

def test_replay_renaming(replay_case: ReplayCase, request):
    summary = summarize_replay(replay_case.replay_file).model_dump(mode="json")
    if request.config.getoption("--update-golden"):
        with replay_case.summary_file.open("w", encoding="utf-8") as f:
            json.dump(summary, f)
    else:
        with replay_case.summary_file.open("r", encoding="utf-8") as f:
            expected = json.load(f)
        assert summary == expected

from shroudstone.renamer import Replay, new_name_for
from tests.conftest import ReplayCase

f1v1 = "{time:%Y-%m-%d %H.%M} {result:.1} {duration} {us} {f1:.1}v{f2:.1} {them} - {map_name}.SGReplay"
fgeneric = (
    "{time:%Y-%m-%d %H.%M} {duration} {players_with_factions} - {map_name}.SGReplay"
)


def test_replay_renaming(replay_case: ReplayCase, request):
    replay = Replay.from_path(replay_case.replay_file)
    assert replay is not None
    new_name = new_name_for(replay, format_1v1=f1v1, format_generic=fgeneric)
    assert isinstance(new_name, str)
    if request.config.getoption("--update-golden"):
        replay_case.expected_name_file.write_text(new_name, encoding="utf-8")
    else:
        assert new_name == replay_case.expected_name_file.read_text(encoding="utf-8")

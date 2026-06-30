from facefinder import constants
from facefinder import data as data_pkg
from facefinder.data.db._base import Manager


def test_package_and_db_public_api() -> None:
    assert hasattr(data_pkg, "atomic")
    assert hasattr(data_pkg, "init_db")
    assert {"Faces", "Images", "Persons"} <= set(data_pkg.__all__)


def test_manager_crud_surface() -> None:
    for method in ("get", "all", "create", "update"):
        assert hasattr(Manager, method)


def test_score_bands_ordered() -> None:
    assert constants.settings.scores.match_strong > constants.settings.scores.match_possible
    assert 0.0 < constants.settings.scores.det_threshold < 1.0

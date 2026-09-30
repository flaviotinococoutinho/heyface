from unittest.mock import Mock

import httpx
import pytest

from app.animals.recognition import ANIMAL_MODEL
from app.config import Settings
from app.errors import DomainError
from app.people.contracts import Search
from app.people.repository import PersonRepository
from app.retrieval.calibration import CalibratedFusion
from app.retrieval.qdrant import Qdrant


def test_database_query_uses_filter_and_named_space_without_vectors_in_response():
    transport = Mock()
    transport.request.return_value = {"points": []}
    store = PersonRepository(transport, Settings().collection)
    query = Search(method="sface", exact=True, filters={"state": "ES"})
    assert store.search("tenant-a", [1.0] * 128, query) == []
    body = transport.request.call_args.kwargs["json"]
    assert body["using"] == "sface"
    assert body["params"]["exact"] is True
    assert body["with_vector"] is False
    assert body["filter"]["must"][0]["match"]["value"] == "tenant-a"


def test_storage_outage_is_not_an_empty_result():
    database = Qdrant(Settings())
    database.client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(503)), base_url="http://qdrant"
    )
    with pytest.raises(DomainError) as error:
        database.request("GET", "/collections")
    assert error.value.status == 503
    assert error.value.code == "storage_unavailable"


def test_calibration_is_monotone_and_explicitly_versioned():
    document = {
        "schema_version": 1,
        "model": ANIMAL_MODEL,
        "global_weight": 0.5,
        "global_curve": {"x": [-1, 0, 1], "y": [0, 0.1, 1]},
        "local_curve": {"x": [0, 5, 20], "y": [0, 0.3, 1]},
    }
    fusion = CalibratedFusion(document)
    assert 0 <= fusion.score(0.4, 5) < fusion.score(0.8, 15) <= 1
    with pytest.raises(ValueError):
        CalibratedFusion(document | {"model": "other-model"})


def test_fusion_fails_closed_without_species_calibration():
    with pytest.raises(DomainError) as error:
        CalibratedFusion.load("unconfigured", "cat")
    assert error.value.code == "calibration_required"

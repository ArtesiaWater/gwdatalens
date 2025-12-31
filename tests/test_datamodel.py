# Tests for datamodel.py SQLAlchemy models
import pytest
from sqlalchemy.orm import Session

from gwdatalens.app.settings import config
from gwdatalens.app.src.data import PostgreSQLDataSource
from gwdatalens.app.src.data.datamodel import (
    GroundwaterLevelDossier,
    MeasurementPointMetadata,
    MeasurementTvp,
    Observation,
    ObservationMetadata,
    TubeDynamic,
    TubeStatic,
    WellStatic,
)


@pytest.fixture
def engine():
    # postgreql database
    return PostgreSQLDataSource(config=config["database"]).engine


def test_query_well(engine):
    with Session(engine) as session:
        wells = session.query(WellStatic).limit(5).all()
        assert isinstance(wells, list)


def test_query_tube_static(engine):
    with Session(engine) as session:
        tubes = session.query(TubeStatic).limit(5).all()
        assert isinstance(tubes, list)


def test_query_tube_dynamic(engine):
    with Session(engine) as session:
        tubes = session.query(TubeDynamic).limit(5).all()
        assert isinstance(tubes, list)


def test_query_groundwater_level_dossier(engine):
    with Session(engine) as session:
        dossiers = session.query(GroundwaterLevelDossier).limit(5).all()
        assert isinstance(dossiers, list)


def test_query_observation(engine):
    with Session(engine) as session:
        obs = session.query(Observation).limit(5).all()
        assert isinstance(obs, list)


def test_query_observation_metadata(engine):
    with Session(engine) as session:
        meta = session.query(ObservationMetadata).limit(5).all()
        assert isinstance(meta, list)


def test_query_measurement_tvp(engine):
    with Session(engine) as session:
        tvps = session.query(MeasurementTvp).limit(5).all()
        assert isinstance(tvps, list)


def test_query_measurement_point_metadata(engine):
    with Session(engine) as session:
        meta = session.query(MeasurementPointMetadata).limit(5).all()
        assert isinstance(meta, list)

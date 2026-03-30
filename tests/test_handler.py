from types import SimpleNamespace

import pytest

from handler import AlreadyProcessedError, ValidationError, _enforce_idempotency, _validate_grabacion


def _grabacion(**overrides):
    base = {
        "fecha_grabacion": "2026-03-30T10:00:00+02:00",
        "lugar": "Madrid",
        "temporada": 4,
        "numero_episodio_1": 32,
        "numero_episodio_2": 33,
        "calendar_creado": False,
        "project_1_ids": [],
        "project_2_ids": [],
        "episodio_1_ids": [],
        "episodio_2_ids": [],
        "procesado_automaticamente": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_validate_grabacion_accepts_valid_payload() -> None:
    _validate_grabacion(_grabacion())


@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_message"),
    [
        ("fecha_grabacion", None, "Fecha de grabación is required"),
        ("lugar", None, "Lugar is required"),
        ("temporada", None, "Temporada is required"),
        ("numero_episodio_1", None, "Número episodio 1 is required"),
        ("numero_episodio_2", None, "Número episodio 2 is required"),
    ],
)
def test_validate_grabacion_rejects_missing_required_fields(
    field_name: str,
    field_value,
    expected_message: str,
) -> None:
    grabacion = _grabacion(**{field_name: field_value})
    with pytest.raises(ValidationError, match=expected_message):
        _validate_grabacion(grabacion)


def test_validate_grabacion_rejects_non_consecutive_episode_numbers() -> None:
    with pytest.raises(ValidationError, match="Número episodio 2 must equal Número episodio 1 \\+ 1"):
        _validate_grabacion(_grabacion(numero_episodio_2=40))


def test_validate_grabacion_requires_datetime_not_just_date() -> None:
    with pytest.raises(ValidationError, match="Fecha de grabación must include date and time"):
        _validate_grabacion(_grabacion(fecha_grabacion="2026-04-04"))


@pytest.mark.parametrize(
    "overrides",
    [
        {"calendar_creado": True},
        {"project_1_ids": ["abc"]},
        {"project_2_ids": ["abc"]},
        {"episodio_1_ids": ["abc"]},
        {"episodio_2_ids": ["abc"]},
        {"procesado_automaticamente": True},
    ],
)
def test_idempotency_blocks_existing_downstream_artifacts(overrides: dict) -> None:
    with pytest.raises(AlreadyProcessedError):
        _enforce_idempotency(_grabacion(**overrides))

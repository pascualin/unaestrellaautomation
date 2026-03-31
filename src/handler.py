from __future__ import annotations

import json
import logging
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from naming import (
    build_calendar_title,
    build_project_or_episode_title,
)


logger = logging.getLogger()
logger.setLevel(logging.INFO)

DEFAULT_RECORDING_TIMEZONE = ZoneInfo("Europe/Madrid")
DEFAULT_RECORDING_HOUR = 20


class ValidationError(Exception):
    pass


class AlreadyProcessedError(Exception):
    pass


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")

    if not body:
        return {}

    if event.get("isBase64Encoded"):
        raise ValueError("Base64-encoded bodies are not supported in this version")

    if isinstance(body, str):
        return json.loads(body)

    if isinstance(body, dict):
        return body

    raise ValueError("Unsupported body format")


def _get_header(event: dict[str, Any], header_name: str) -> str | None:
    headers = event.get("headers") or {}
    lower_map = {str(k).lower(): v for k, v in headers.items()}
    value = lower_map.get(header_name.lower())
    return str(value) if value is not None else None


def _extract_grabacion_page_id(body: dict[str, Any]) -> str | None:
    raw_value = body.get("grabacion_page_id")
    if isinstance(raw_value, str):
        return raw_value

    if isinstance(raw_value, dict):
        formula = raw_value.get("formula")
        if isinstance(formula, dict):
            formula_string = formula.get("string")
            if isinstance(formula_string, str) and formula_string:
                return formula_string

    data = body.get("data")
    if isinstance(data, dict):
        properties = data.get("properties")
        if isinstance(properties, dict):
            property_value = properties.get("grabacion_page_id")
            if isinstance(property_value, dict):
                formula = property_value.get("formula")
                if isinstance(formula, dict):
                    formula_string = formula.get("string")
                    if isinstance(formula_string, str) and formula_string:
                        return formula_string

        data_id = data.get("id")
        if isinstance(data_id, str) and data_id:
            return data_id

    return None


def _build_notion_page_url(page_id: str) -> str:
    return f"https://www.notion.so/{page_id.replace('-', '')}"


def _normalize_fecha_grabacion(value: str) -> str:
    if "T" in value:
        return value

    parsed_date = date.fromisoformat(value)
    normalized = datetime.combine(
        parsed_date,
        time(hour=DEFAULT_RECORDING_HOUR, minute=0, tzinfo=DEFAULT_RECORDING_TIMEZONE),
    )
    return normalized.isoformat()


def _build_calendar_description(grabacion: Any) -> str:
    guest_names = [inv.name for inv in grabacion.invitados]
    guest_line = ", ".join(guest_names) if guest_names else "Sin invitados"
    return "\n".join(
        [
            f"Temporada: {grabacion.temporada}",
            f"Episodios: {grabacion.numero_episodio_1} y {grabacion.numero_episodio_2}",
            f"Invitados: {guest_line}",
            f"Grabación en Notion: {_build_notion_page_url(grabacion.page_id)}",
        ]
    )


def _validate_grabacion(grabacion: Any) -> None:
    validations = [
        (grabacion.fecha_grabacion, "Fecha de grabación is required"),
        (grabacion.lugar, "Lugar is required"),
        (grabacion.temporada is not None, "Temporada is required"),
        (grabacion.numero_episodio_1 is not None, "Número episodio 1 is required"),
        (grabacion.numero_episodio_2 is not None, "Número episodio 2 is required"),
    ]
    for is_valid, error_message in validations:
        if not is_valid:
            raise ValidationError(error_message)

    if grabacion.numero_episodio_2 != grabacion.numero_episodio_1 + 1:
        raise ValidationError("Número episodio 2 must equal Número episodio 1 + 1")


def _enforce_idempotency(grabacion: Any) -> None:
    if grabacion.procesado_automaticamente:
        raise AlreadyProcessedError("Grabación already processed automatically")

    if (
        grabacion.calendar_creado
        or grabacion.project_1_ids
        or grabacion.project_2_ids
        or grabacion.episodio_1_ids
        or grabacion.episodio_2_ids
    ):
        raise AlreadyProcessedError("Grabación already has downstream artefacts")


def _log_json(message: str, payload: dict[str, Any]) -> None:
    logger.info("%s: %s", message, json.dumps(payload, ensure_ascii=False))


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    from config import load_config
    from google_calendar_client import GoogleCalendarClient
    from notion_client import NotionClient

    notion = None
    grabacion = None
    try:
        config = load_config()
        provided_secret = _get_header(event, "x-webhook-secret")

        if provided_secret != config.webhook_shared_secret:
            logger.warning("Unauthorized request: invalid webhook secret")
            return _response(401, {"ok": False, "error": "unauthorized"})

        body = _parse_body(event)
        grabacion_page_id = _extract_grabacion_page_id(body)

        if not grabacion_page_id:
            logger.warning("Missing grabacion_page_id in payload")
            return _response(400, {"ok": False, "error": "missing grabacion_page_id"})

        _log_json("start", {"grabacion_page_id": grabacion_page_id})

        notion = NotionClient(config.notion_token)
        grabacion = notion.get_grabacion(grabacion_page_id)

        _log_json(
            "grabacion_loaded",
            {
                "page_id": grabacion.page_id,
                "title": grabacion.title,
                "fecha_grabacion": grabacion.fecha_grabacion,
                "lugar": grabacion.lugar,
                "temporada": grabacion.temporada,
                "numero_episodio_1": grabacion.numero_episodio_1,
                "numero_episodio_2": grabacion.numero_episodio_2,
                "invitados": [inv.name for inv in grabacion.invitados],
                "project_1_ids": grabacion.project_1_ids,
                "project_2_ids": grabacion.project_2_ids,
                "episodio_1_ids": grabacion.episodio_1_ids,
                "episodio_2_ids": grabacion.episodio_2_ids,
                "calendar_creado": grabacion.calendar_creado,
                "estado_preparacion": grabacion.estado_preparacion,
                "procesado_automaticamente": grabacion.procesado_automaticamente,
                "ultimo_error_automatizacion": grabacion.ultimo_error_automatizacion,
            },
        )

        _log_json("validation", {"page_id": grabacion.page_id})
        _validate_grabacion(grabacion)
        grabacion.fecha_grabacion = _normalize_fecha_grabacion(grabacion.fecha_grabacion)
        _enforce_idempotency(grabacion)

        guest_names = [invitado.name for invitado in grabacion.invitados]
        guest_ids = [invitado.page_id for invitado in grabacion.invitados]

        project_1_title = build_project_or_episode_title(
            grabacion.temporada,
            grabacion.numero_episodio_1,
            [],
        )
        project_2_title = build_project_or_episode_title(
            grabacion.temporada,
            grabacion.numero_episodio_2,
            guest_names,
        )
        calendar_title = build_calendar_title(
            grabacion.temporada,
            grabacion.numero_episodio_1,
            grabacion.numero_episodio_2,
            guest_names,
        )

        calendar = GoogleCalendarClient(
            client_id=config.google_client_id,
            client_secret=config.google_client_secret,
            refresh_token=config.google_refresh_token,
        )

        _log_json("calendar_creation", {"summary": calendar_title})
        calendar_event = calendar.create_event(
            calendar_id=config.google_calendar_id,
            summary=calendar_title,
            start_datetime=grabacion.fecha_grabacion,
            location=grabacion.lugar,
            description=_build_calendar_description(grabacion),
        )

        _log_json("project_creation", {"project": 1, "name": project_1_title})
        project_1 = notion.create_project(
            projects_database_id=config.notion_projects_ds_id,
            title=project_1_title,
            area_page_id=config.notion_area_una_estrella_id,
            due_date=grabacion.fecha_grabacion,
        )

        _log_json("project_creation", {"project": 2, "name": project_2_title})
        project_2 = notion.create_project(
            projects_database_id=config.notion_projects_ds_id,
            title=project_2_title,
            area_page_id=config.notion_area_una_estrella_id,
            due_date=grabacion.fecha_grabacion,
        )

        _log_json("episode_creation", {"episode": 1, "title": project_1_title})
        episodio_1 = notion.create_episode(
            episodes_database_id=config.notion_episodios_ds_id,
            title=project_1_title,
            fecha_grabacion=grabacion.fecha_grabacion,
            project_page_id=project_1.page_id,
            invitado_ids=[],
        )

        _log_json("episode_creation", {"episode": 2, "title": project_2_title})
        episodio_2 = notion.create_episode(
            episodes_database_id=config.notion_episodios_ds_id,
            title=project_2_title,
            fecha_grabacion=grabacion.fecha_grabacion,
            project_page_id=project_2.page_id,
            invitado_ids=guest_ids,
        )

        _log_json("source_update", {"page_id": grabacion.page_id})
        notion.update_grabacion_success(
            page_id=grabacion.page_id,
            project_1_id=project_1.page_id,
            project_2_id=project_2.page_id,
            episodio_1_id=episodio_1.page_id,
            episodio_2_id=episodio_2.page_id,
        )

        _log_json(
            "success",
            {
                "grabacion_page_id": grabacion.page_id,
                "calendar_event_id": calendar_event.event_id,
                "project_1_id": project_1.page_id,
                "project_2_id": project_2.page_id,
                "episodio_1_id": episodio_1.page_id,
                "episodio_2_id": episodio_2.page_id,
            },
        )
        return _response(
            200,
            {
                "ok": True,
                "message": "automation completed successfully",
                "result": {
                    "grabacion_page_id": grabacion.page_id,
                    "calendar_event_id": calendar_event.event_id,
                    "project_1_id": project_1.page_id,
                    "project_2_id": project_2.page_id,
                    "episodio_1_id": episodio_1.page_id,
                    "episodio_2_id": episodio_2.page_id,
                },
            },
        )

    except AlreadyProcessedError as exc:
        logger.info("No-op: %s", str(exc))
        return _response(200, {"ok": True, "message": str(exc), "noop": True})
    except ValidationError as exc:
        if notion is not None and grabacion is not None:
            notion.update_grabacion_error(grabacion.page_id, str(exc))
        logger.warning("Validation failed: %s", str(exc))
        return _response(400, {"ok": False, "error": str(exc)})
    except Exception as exc:
        logger.exception("Unhandled error")
        if notion is not None and grabacion is not None:
            try:
                notion.update_grabacion_error(grabacion.page_id, str(exc))
            except Exception:
                logger.exception("Failed to write automation error back to Notion")
        return _response(500, {"ok": False, "error": str(exc)})

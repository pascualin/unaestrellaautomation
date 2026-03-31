from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


NOTION_API_VERSION = "2022-06-28"
EPISODIO_TEMPLATE_ID = "2a964f5c-cfab-81ce-90a3-e6bac70da6bc"


@dataclass
class InvitadoData:
    page_id: str
    name: str


@dataclass
class GrabacionData:
    page_id: str
    title: str
    fecha_grabacion: str | None
    lugar: str | None
    temporada: int | None
    numero_episodio_1: int | None
    numero_episodio_2: int | None
    invitados: list[InvitadoData]
    project_1_ids: list[str]
    project_2_ids: list[str]
    episodio_1_ids: list[str]
    episodio_2_ids: list[str]
    calendar_creado: bool
    estado_preparacion: str | None
    procesado_automaticamente: bool
    ultimo_error_automatizacion: str | None


@dataclass
class CreatedPageData:
    page_id: str
    url: str | None


class NotionClient:
    def __init__(self, notion_token: str) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            }
        )

    def fetch_page(self, page_id: str) -> dict[str, Any]:
        response = self.session.get(f"https://api.notion.com/v1/pages/{page_id}", timeout=30)
        response.raise_for_status()
        return response.json()

    def create_page(
        self,
        parent_database_id: str,
        properties: dict[str, Any],
        template: dict[str, Any] | None = None,
    ) -> CreatedPageData:
        payload = {
            "parent": {"database_id": parent_database_id},
            "properties": properties,
        }
        if template is not None:
            payload["template"] = template

        response = self.session.post(
            "https://api.notion.com/v1/pages",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        page = response.json()
        return CreatedPageData(page_id=page["id"], url=page.get("url"))

    def update_page_properties(self, page_id: str, properties: dict[str, Any]) -> None:
        response = self.session.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            json={"properties": properties},
            timeout=30,
        )
        response.raise_for_status()

    def fetch_page_title(self, page_id: str) -> str:
        page = self.fetch_page(page_id)
        props = page.get("properties", {})

        title_prop = None
        for prop in props.values():
            if prop.get("type") == "title":
                title_prop = prop
                break

        if not title_prop:
            return page_id

        return self._read_title_property(title_prop) or page_id

    def get_grabacion(self, page_id: str) -> GrabacionData:
        page = self.fetch_page(page_id)
        props = page["properties"]

        invitados_refs = self._read_relation(props.get("Invitado"))
        invitados = [
            InvitadoData(page_id=inv_id, name=self.fetch_page_title(inv_id))
            for inv_id in invitados_refs
        ]

        return GrabacionData(
            page_id=page["id"],
            title=self._read_title_property(props["Name"]),
            fecha_grabacion=self._read_date_start(props.get("Fecha de grabación")),
            lugar=self._read_rich_text(props.get("Lugar")),
            temporada=self._read_number(props.get("Temporada")),
            numero_episodio_1=self._read_number(props.get("Número episodio 1")),
            numero_episodio_2=self._read_number(props.get("Número episodio 2")),
            invitados=invitados,
            project_1_ids=self._read_relation(props.get("Project 1")),
            project_2_ids=self._read_relation(props.get("Project 2")),
            episodio_1_ids=self._read_relation(props.get("Episodio 1")),
            episodio_2_ids=self._read_relation(props.get("Episodio 2")),
            calendar_creado=self._read_checkbox(props.get("Calendar creado")),
            estado_preparacion=self._read_status(props.get("Estado preparación")),
            procesado_automaticamente=self._read_checkbox(
                props.get("Procesado automáticamente")
            ),
            ultimo_error_automatizacion=self._read_rich_text(
                props.get("Último error automatización")
            ),
        )

    def create_project(
        self,
        projects_database_id: str,
        title: str,
        area_page_id: str,
        due_date: str,
    ) -> CreatedPageData:
        return self.create_page(
            parent_database_id=projects_database_id,
            properties={
                "Name": self._title_value(title),
                "Areas": self._relation_value([area_page_id]),
                "Due Date": self._date_value(due_date),
                "Scope": self._select_value("personal"),
            },
            template={"type": "default"},
        )

    def create_episode(
        self,
        episodes_database_id: str,
        title: str,
        fecha_grabacion: str,
        project_page_id: str,
        invitado_ids: list[str],
    ) -> CreatedPageData:
        properties = {
            "Título": self._title_value(title),
            "Tipo": self._select_value("Episodio"),
            "Fecha de grabación": self._date_value(fecha_grabacion),
            "Episodio": self._relation_value([project_page_id]),
        }
        if invitado_ids:
            properties["Invitados"] = self._relation_value(invitado_ids)
        return self.create_page(
            parent_database_id=episodes_database_id,
            properties=properties,
            template={"type": "template_id", "template_id": EPISODIO_TEMPLATE_ID},
        )

    def update_grabacion_success(
        self,
        page_id: str,
        project_1_id: str,
        project_2_id: str,
        episodio_1_id: str,
        episodio_2_id: str,
    ) -> None:
        self.update_page_properties(
            page_id,
            {
                "Project 1": self._relation_value([project_1_id]),
                "Project 2": self._relation_value([project_2_id]),
                "Episodio 1": self._relation_value([episodio_1_id]),
                "Episodio 2": self._relation_value([episodio_2_id]),
                "Calendar creado": {"checkbox": True},
                "Estado preparación": {"status": {"name": "En preparación"}},
                "Procesado automáticamente": {"checkbox": True},
                "Último error automatización": self._rich_text_value(""),
            },
        )

    def update_grabacion_error(self, page_id: str, error_message: str) -> None:
        self.update_page_properties(
            page_id,
            {
                "Procesado automáticamente": {"checkbox": False},
                "Último error automatización": self._rich_text_value(error_message),
            },
        )

    @staticmethod
    def _read_title_property(prop: dict[str, Any] | None) -> str:
        if not prop or prop.get("type") != "title":
            return ""
        return "".join(item.get("plain_text", "") for item in prop.get("title", []))

    @staticmethod
    def _read_rich_text(prop: dict[str, Any] | None) -> str | None:
        if not prop:
            return None

        prop_type = prop.get("type")
        if prop_type not in {"rich_text", "title"}:
            return None

        key = "rich_text" if prop_type == "rich_text" else "title"
        items = prop.get(key, [])
        value = "".join(item.get("plain_text", "") for item in items).strip()
        return value or None

    @staticmethod
    def _read_number(prop: dict[str, Any] | None) -> int | None:
        if not prop or prop.get("type") != "number":
            return None

        value = prop.get("number")
        if value is None:
            return None

        return int(value)

    @staticmethod
    def _read_date_start(prop: dict[str, Any] | None) -> str | None:
        if not prop or prop.get("type") != "date":
            return None

        date_value = prop.get("date")
        if not date_value:
            return None

        return date_value.get("start")

    @staticmethod
    def _read_relation(prop: dict[str, Any] | None) -> list[str]:
        if not prop or prop.get("type") != "relation":
            return []

        return [item["id"] for item in prop.get("relation", [])]

    @staticmethod
    def _read_checkbox(prop: dict[str, Any] | None) -> bool:
        if not prop or prop.get("type") != "checkbox":
            return False
        return bool(prop.get("checkbox", False))

    @staticmethod
    def _read_status(prop: dict[str, Any] | None) -> str | None:
        if not prop or prop.get("type") != "status":
            return None

        status = prop.get("status")
        if not status:
            return None

        return status.get("name")

    @staticmethod
    def _title_value(value: str) -> dict[str, Any]:
        return {
            "title": [
                {
                    "type": "text",
                    "text": {"content": value},
                }
            ]
        }

    @staticmethod
    def _rich_text_value(value: str) -> dict[str, Any]:
        return {
            "rich_text": (
                [
                    {
                        "type": "text",
                        "text": {"content": value},
                    }
                ]
                if value
                else []
            )
        }

    @staticmethod
    def _relation_value(page_ids: list[str]) -> dict[str, Any]:
        return {"relation": [{"id": page_id} for page_id in page_ids]}

    @staticmethod
    def _date_value(value: str) -> dict[str, Any]:
        return {"date": {"start": value}}

    @staticmethod
    def _select_value(value: str) -> dict[str, Any]:
        return {"select": {"name": value}}

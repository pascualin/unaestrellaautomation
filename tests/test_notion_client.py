from notion_client import CreatedPageData, NotionClient


def test_create_project_sets_status_open() -> None:
    captured = {}
    client = NotionClient("notion-token")

    def create_page(parent_database_id, properties, template=None):
        captured["parent_database_id"] = parent_database_id
        captured["properties"] = properties
        captured["template"] = template
        return CreatedPageData(page_id="project-page-id", url=None)

    client.create_page = create_page

    page = client.create_project(
        projects_database_id="projects-db-id",
        title="S04E36",
        area_page_id="area-page-id",
        due_date="2026-04-06T20:00:00+02:00",
    )

    assert page.page_id == "project-page-id"
    assert captured["properties"]["Status"] == {"status": {"name": "Open"}}

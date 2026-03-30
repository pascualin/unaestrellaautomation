from naming import (
    build_calendar_title,
    build_project_or_episode_title,
    render_calendar_guest_list,
    render_full_guest_list,
)


def test_full_guest_rendering_variants() -> None:
    assert render_full_guest_list([]) == ""
    assert render_full_guest_list(["Nacho García"]) == "Nacho García"
    assert render_full_guest_list(["Raúl Massana", "Mayte"]) == "Raúl Massana y Mayte"
    assert (
        render_full_guest_list(["Raúl Massana", "Mayte", "Jose"])
        == "Raúl Massana, Mayte y Jose"
    )


def test_calendar_guest_rendering_variants() -> None:
    assert render_calendar_guest_list([]) == ""
    assert render_calendar_guest_list(["Nacho García"]) == "Nacho García"
    assert render_calendar_guest_list(["Raúl Massana", "Mayte"]) == "Raúl Massana y Mayte"
    assert render_calendar_guest_list(["Raúl Massana", "Mayte", "Jose"]) == "Raúl Massana +2"


def test_project_or_episode_title_without_guests() -> None:
    assert build_project_or_episode_title(4, 32, []) == "S04E32"


def test_project_or_episode_title_with_full_guest_names() -> None:
    assert (
        build_project_or_episode_title(4, 33, ["Raúl Massana", "Mayte", "Jose"])
        == "S04E33 - Raúl Massana, Mayte y Jose"
    )


def test_calendar_title_with_compact_many_guest_format() -> None:
    assert (
        build_calendar_title(4, 32, 33, ["Raúl Massana", "Mayte", "Jose"])
        == "Grabación S04E32/33 - Raúl Massana +2"
    )

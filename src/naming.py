from __future__ import annotations


def format_episode_code(temporada: int, numero_episodio: int) -> str:
    return f"S{temporada:02d}E{numero_episodio}"


def render_full_guest_list(guest_names: list[str]) -> str:
    if not guest_names:
        return ""
    if len(guest_names) == 1:
        return guest_names[0]
    if len(guest_names) == 2:
        return f"{guest_names[0]} y {guest_names[1]}"
    return f"{', '.join(guest_names[:-1])} y {guest_names[-1]}"


def render_calendar_guest_list(guest_names: list[str]) -> str:
    if not guest_names:
        return ""
    if len(guest_names) < 3:
        return render_full_guest_list(guest_names)
    return f"{guest_names[0]} +{len(guest_names) - 1}"


def build_project_or_episode_title(
    temporada: int,
    numero_episodio: int,
    guest_names: list[str],
) -> str:
    base = format_episode_code(temporada, numero_episodio)
    if not guest_names:
        return base
    return f"{base} - {render_full_guest_list(guest_names)}"


def build_calendar_title(
    temporada: int,
    numero_episodio_1: int,
    numero_episodio_2: int,
    guest_names: list[str],
) -> str:
    base = f"Grabación S{temporada:02d}E{numero_episodio_1}/{numero_episodio_2}"
    rendered_guests = render_calendar_guest_list(guest_names)
    if not rendered_guests:
        return base
    return f"{base} - {rendered_guests}"

# -*- coding: utf-8 -*-

# Colorful Tags for Anki
#
# Copyright (C) 2018-2021  Aristotelis P. <https//glutanimate.com/>
# Copyright (C) 2021  RumovZ <gp5glkw78@relay.firefox.com>
# Coypright (C) 2014  Patrice Neff <http://patrice.ch/>

from typing import TYPE_CHECKING
import json
import re

from aqt.browser import SidebarItemType  # type: ignore
from aqt.qt import QColor, QColorDialog, QMenu, QModelIndex

from ..data import user_data
from .item import PatchedSideBarItem


_TAG_RE = re.compile(r'-?tag:(?:"([^"]+)"|([^\s()]+))')

def extract_tags_from_filter(filter_str: str) -> list[str]:
    """
    Extracts all tags from the browser filter string. 
    Negative tags (-tag:...) are skipped — we don’t need them for the installation.
    """
    if not filter_str:
        return []

    tags: list[str] = []
    for m in _TAG_RE.finditer(filter_str):        
        if m.group(0).startswith("-"):
            continue
        tag = m.group(1) or m.group(2)
        if tag and tag not in tags:
            tags.append(tag)
    return tags



def _get_tag_data(tag_name: str) -> dict:
    """Returns (creating it if necessary) a dictionary of tag settings."""
    return user_data.tags.setdefault(tag_name, {})


def _cleanup_tag_if_empty(tag_name: str) -> None:
    """Deletes a tag entry if no settings remain within it."""
    tag = user_data.tags.get(tag_name)
    if tag is not None and not tag:
        del user_data.tags[tag_name]


# ---------- Batch operations ----------

def pin_tags_from_filter(sidebar: "SidebarTreeView", filter_str: str, pin: bool = True) -> int:
    """Pins (pin=True) or unpins (pin=False) all tags in the filter. 
Returns the number of affected tags."""
    tags = extract_tags_from_filter(filter_str)
    if not tags:
        return 0

    for tag_name in tags:
        tag = _get_tag_data(tag_name)
        if pin:
            tag["pin"] = True
        else:
            tag.pop("pin", None)
            _cleanup_tag_if_empty(tag_name)

    user_data.save()
    # Pinning affects sorting — a full refresh is required.
    sidebar.refresh()
    _refresh_editor(sidebar)
    return len(tags)


def toggle_pin_tags_from_filter(sidebar: "SidebarTreeView", filter_str: str) -> int:
    """Inverts the 'pin' status for EACH tag in the filter individually:
pinned tags become unpinned, and unpinned tags become pinned. 
Returns the number of affected tags."""
    tags = extract_tags_from_filter(filter_str)
    if not tags:
        return 0

    for tag_name in tags:
        tag = _get_tag_data(tag_name)
        if tag.get("pin", False):
            # it was secured — we’re removing it
            tag.pop("pin", None)
            _cleanup_tag_if_empty(tag_name)
        else:
            # was not secured - secure it
            tag["pin"] = True

    user_data.save()
    # 'pin' affects sorting (pinned items move to the top) — a full refresh is required
    sidebar.refresh()
    _refresh_editor(sidebar)
    return len(tags)


def assign_color_to_tags_from_filter(
    sidebar: "SidebarTreeView",
    filter_str: str,
    color: QColor | None = None,
) -> int:
    """Assigns a color to all tags from the filter. 
If color=None, it opens a single, shared QColorDialog. 
Returns the number of affected tags."""
    tags = extract_tags_from_filter(filter_str)
    if not tags:
        return 0

    if color is None:
        initial = QColor("#0000FF")
        dialog = QColorDialog(initial, parent=sidebar)
        color = dialog.getColor(initial)
        if not color.isValid():
            return 0

    color_name = color.name()
    for tag_name in tags:
        _get_tag_data(tag_name)["color"] = color_name

    user_data.save()
    sidebar.refresh()
    # sidebar.model().dataChanged.emit(
        # sidebar.model().index(0, 0),
        # sidebar.model().index(0, 0),
    # )
    # sidebar.viewport().update()
    _refresh_editor(sidebar)
    return len(tags)


def remove_color_from_tags_from_filter(sidebar: "SidebarTreeView", filter_str: str) -> int:
    """Removes the color from all tags in the filter. Returns the number of affected tags."""
    tags = extract_tags_from_filter(filter_str)
    if not tags:
        return 0

    affected = 0
    for tag_name in tags:
        tag = user_data.tags.get(tag_name)
        if tag and "color" in tag:
            del tag["color"]
            _cleanup_tag_if_empty(tag_name)
            affected += 1

    if affected:
        user_data.save()
        sidebar.refresh()
        # sidebar.model().dataChanged.emit(
            # sidebar.model().index(0, 0),
            # sidebar.model().index(0, 0),
        # )
        # sidebar.viewport().update()
        _refresh_editor(sidebar)
    return affected




if TYPE_CHECKING:
    from aqt.browser import SidebarTreeView  # type: ignore


def maybe_add_context_actions(
    sidebar: "SidebarTreeView",
    menu: QMenu,
    item: PatchedSideBarItem,
    index: QModelIndex,
):
    if item.item_type != SidebarItemType.TAG:
        return

    # Attempting to retrieve the browser filter
    browser = getattr(sidebar, "browser", None)
    filter_str = ""
    if browser is not None:
        try:
            filter_str = browser.current_search()
        except Exception:
            filter_str = ""

    filter_tags = extract_tags_from_filter(filter_str)
    # We display batch actions only if there are actually multiple tags in the filter.
    multi = len(filter_tags) > 1
    
    # print("filter_str=", filter_str)

    menu.addSeparator()

    # --- Single actions (as before) ---
    pin_action = "Unpin" if item.is_pinned else "Pin"
    menu.addAction(pin_action, lambda: _toggle_pin(sidebar, item))
    menu.addAction("Assign Color", lambda: _assign_color(sidebar, item, index))
    if item.color:
        menu.addAction("Remove Color", lambda: _remove_color(sidebar, item, index))

    # --- Batch actions ---
    if multi:
        menu.addSeparator()
        sub = menu.addMenu(f"Filter tags ({len(filter_tags)})")

        sub.addAction(
            "Pin all",
            lambda: pin_tags_from_filter(sidebar, filter_str, pin=True),
        )
        sub.addAction(
            "Unpin all",
            lambda: pin_tags_from_filter(sidebar, filter_str, pin=False),
        )
        sub.addAction(
            "Toggle pin (all)",
            lambda: toggle_pin_tags_from_filter(sidebar, filter_str),
        )
        sub.addSeparator()
        sub.addAction(
            "Assign color to all…",
            lambda: assign_color_to_tags_from_filter(sidebar, filter_str),
        )
        sub.addAction(
            "Remove color from all",
            lambda: remove_color_from_tags_from_filter(sidebar, filter_str),
        )


def _toggle_pin(sidebar: "SidebarTreeView", item: PatchedSideBarItem):
    if tag := user_data.tags.get(item.full_name, None):
        if tag.get("pin", False):
            del tag["pin"]
            if not len(tag):
                del user_data.tags[item.full_name]
        else:
            tag["pin"] = True
    else:
        user_data.tags[item.full_name] = {"pin": True}
    user_data.save()

    # Normal refresh here because pinning moves the tag to the top
    sidebar.refresh()


def _assign_color(sidebar: "SidebarTreeView", item: PatchedSideBarItem, index: QModelIndex):
    color = QColor(item.color or "#0000FF")
    dialog = QColorDialog(color, parent=sidebar)
    color = dialog.getColor(color)
    if color.isValid():
        if not (tag := user_data.tags.get(item.full_name, None)):
            tag = user_data.tags[item.full_name] = {}  # type: ignore
        tag["color"] = color.name()
        user_data.save()

        # THE FIX: Tell the tag in memory about its new color!
        item.color = color.name()

        sidebar.model().dataChanged.emit(index, index)
        sidebar.viewport().update()

        _refresh_editor(sidebar)


def _remove_color(sidebar: "SidebarTreeView", item: PatchedSideBarItem, index: QModelIndex):
    if tag := user_data.tags.get(item.full_name, None):
        if "color" in tag:
            del tag["color"]
            if not len(tag):
                del user_data.tags[item.full_name]
            user_data.save()

            # THE FIX: Tell the tag in memory that its color is gone!
            item.color = None

            sidebar.model().dataChanged.emit(index, index)
            sidebar.viewport().update()

            _refresh_editor(sidebar)


def _refresh_editor(sidebar):
    try:
        import json
        colors = {t: s["color"] for t, s in user_data.tags.items() if "color" in s}
        js = f"""
        if (typeof window !== 'undefined') {{
            window.tagColors = {json.dumps(colors)};

            document.querySelectorAll('button[data-addon-tag]').forEach(el => {{
                // Wipe the optimizer's memory so it knows to repaint!
                delete el.dataset.currentColor;

                // Wash off the old colors
                el.style.removeProperty('background');
                el.style.removeProperty('background-color');
                el.style.removeProperty('color');
                el.querySelectorAll('span, svg, path').forEach(s => {{
                    s.style.removeProperty('color');
                    s.style.removeProperty('background');
                    s.style.removeProperty('fill');
                }});
            }});
        }}
        """
        sidebar.window().editor.web.eval(js)
    except Exception:
        pass

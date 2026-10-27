"""Keeps a box on the LGU's Organizational Chart (OrgChartNode, Super Admin)
and its Municipal Official card on the About Us page (AboutOfficial) the same:
name, position and photo. Each side gets its own copy of the photo file, so
removing one never breaks the other."""
import os

from django.core.files.base import ContentFile

from admin_dashboard.models import AboutOfficial
from .models import OrgChartNode


def _copy_photo(src, dst):
    """Copies the image in file field `src` into file field `dst` (not saved)."""
    if not src:
        return
    try:
        src.open("rb")
        data = src.read()
        src.close()
    except Exception:
        return            # the file is missing from storage: leave dst as it is
    if dst:
        dst.delete(save=False)
    dst.save(os.path.basename(src.name), ContentFile(data), save=False)


def box_to_official(node, photo_changed=False, photo_removed=False):
    """The box was saved on the chart: update its official's card."""
    o = node.official
    if o is None:
        return
    o.name = node.name[:150]
    if node.position:
        o.position = node.position[:150]
    if photo_changed and node.photo:
        _copy_photo(node.photo, o.photo)
    elif photo_removed and o.photo:
        o.photo.delete(save=False)
        o.photo = None
    elif node.photo and not o.photo:
        _copy_photo(node.photo, o.photo)
    elif o.photo and not node.photo:
        _copy_photo(o.photo, node.photo)
        node.save(update_fields=["photo", "updated_at"])
    o.save()


def official_to_box(o, photo_changed=False):
    """The official was saved in the Municipal Officials tab: update its box."""
    node = linked_box(o)
    if node is None:
        return
    node.name = o.name[:150]
    node.position = o.position[:200]
    if photo_changed and o.photo:
        _copy_photo(o.photo, node.photo)
    elif o.photo and not node.photo:
        _copy_photo(o.photo, node.photo)
    elif node.photo and not o.photo:
        _copy_photo(node.photo, o.photo)
        o.save(update_fields=["photo"])
    node.save()


def linked_box(o):
    return OrgChartNode.objects.filter(official=o).first() if o and o.pk else None


def new_official_from_box(node):
    """'Add as a new Municipal Official' on a chart box."""
    o = AboutOfficial(name=node.name[:150], position=(node.position or "")[:150],
                      order=AboutOfficial.objects.count())
    if node.photo:
        _copy_photo(node.photo, o.photo)
    o.save()
    node.official = o
    node.save(update_fields=["official", "updated_at"])
    return o


def sync_box(node, photo_changed=False, photo_removed=False):
    """Called each time a box of the LGU chart is saved. A person box is always
    one of the Municipal Officials: it is created (or found by the same name)
    the first time, and updated after that. A section box is never an official.
    Returns a note for the success message."""
    if node.kind != OrgChartNode.KIND_PERSON:
        if node.official_id:
            delete_official(node.official)
            node.official = None
            node.save(update_fields=["official", "updated_at"])
            return " It was taken out of the Municipal Officials (a section is not a person)."
        return ""
    if node.official_id:
        box_to_official(node, photo_changed=photo_changed, photo_removed=photo_removed)
        return " The Municipal Officials (About Us page) were updated too."
    same_name = (AboutOfficial.objects.filter(chart_node__isnull=True, name__iexact=node.name.strip())
                 .order_by("order", "id").first())
    if same_name:
        node.official = same_name
        node.save(update_fields=["official", "updated_at"])
        box_to_official(node, photo_changed=bool(node.photo))
        return f' It is now connected to "{same_name.name}" in the Municipal Officials (About Us page).'
    new_official_from_box(node)
    return " It was also added to the Municipal Officials (About Us page)."


def delete_official(o):
    if o is None:
        return
    if o.photo:
        o.photo.delete(save=False)
    o.delete()


def new_box_for_official(o, office, parent=None):
    """'Add a new box in the org chart' from the Municipal Officials tab."""
    from .org_chart import next_order
    node = OrgChartNode(office=office, kind=OrgChartNode.KIND_PERSON, name=o.name[:150],
                        position=o.position[:200], parent=parent, official=o,
                        order=next_order(office, parent.pk if parent else None))
    if o.photo:
        _copy_photo(o.photo, node.photo)
    node.save()
    return node


def remove_box(node):
    """Removes a box; the boxes under it move up to its parent (same as the chart editor)."""
    OrgChartNode.objects.filter(office=node.office_id, parent=node).update(parent=node.parent)
    if node.photo:
        node.photo.delete(save=False)
    node.delete()
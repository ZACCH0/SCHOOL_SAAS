import datetime

import pytest
from django.db.models.query import QuerySet
from django.urls import reverse
from django.utils import timezone

from apps.schools.models import Membership

from .models import AuditLog

pytestmark = pytest.mark.django_db

TOKEN = "t15a"
UNIQUE = "t15a-only"


def add_entry(school, action=UNIQUE, actor_label="manager-1", target_repr="A student"):
    return AuditLog.objects.create(
        school=school, action=action, actor_label=actor_label, target_repr=target_repr
    )


def backdate(entry, when):
    QuerySet(AuditLog).filter(pk=entry.pk).update(created_at=when)


def test_anonymous_is_sent_to_login(client):
    response = client.get(reverse("audit:list"))
    assert response.status_code == 302 and "/login" in response.url


def test_staff_roles_with_other_duties_get_403(client, school_a, login_as):
    for role in (Membership.Role.TEACHER, Membership.Role.BURSAR, Membership.Role.PARENT):
        login_as(school_a, role)
        assert client.get(reverse("audit:list")).status_code == 403


def test_owner_sees_entries_newest_first(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    first = add_entry(school_a, action=f"{TOKEN}.first")
    second = add_entry(school_a, action=f"{TOKEN}.second")
    response = client.get(reverse("audit:list"), {"q": TOKEN})
    page = response.context["page_obj"].object_list
    actions = [entry.action for entry in page]
    assert actions == [second.action, first.action]


def test_other_school_entries_never_appear(client, school_a, school_b, login_as):
    login_as(school_a, Membership.Role.OWNER)
    add_entry(school_a, action=f"{TOKEN}.keep")
    add_entry(school_b, action=f"{TOKEN}.leak")
    response = client.get(reverse("audit:list"), {"q": TOKEN})
    page = response.context["page_obj"].object_list
    assert [entry.action for entry in page] == [f"{TOKEN}.keep"]


def test_search_matches_who_action_and_target(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    by_actor = add_entry(school_a, action=f"{TOKEN}.a", actor_label="search-user")
    by_action = add_entry(school_a, action=f"{TOKEN}.search-me")
    by_target = add_entry(school_a, action=f"{TOKEN}.b", target_repr="search target")
    response = client.get(reverse("audit:list"), {"q": "search"})
    actions = {entry.action for entry in response.context["page_obj"].object_list}
    assert actions == {by_actor.action, by_action.action, by_target.action}


def test_search_with_no_match_shows_empty_state(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    add_entry(school_a)
    response = client.get(reverse("audit:list"), {"q": "no-such-entry"})
    assert not response.context["page_obj"].object_list
    assert "No audit entries" in response.content.decode()


def test_date_range_filters_entries(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    add_entry(school_a, action=f"{TOKEN}.today")
    old = add_entry(school_a, action=f"{TOKEN}.old")
    backdate(
        old,
        timezone.make_aware(datetime.datetime(2026, 1, 15, 9, 30), datetime.timezone.utc),
    )
    in_range = client.get(reverse("audit:list"), {"q": TOKEN, "from": "2026-01-10", "to": "2026-01-20"})
    in_range_actions = [entry.action for entry in in_range.context["page_obj"].object_list]
    assert in_range_actions == [f"{TOKEN}.old"]
    everything = client.get(reverse("audit:list"), {"q": TOKEN, "from": "2026-01-01"})
    everything_actions = {entry.action for entry in everything.context["page_obj"].object_list}
    assert everything_actions == {f"{TOKEN}.old", f"{TOKEN}.today"}


def test_garbage_dates_are_ignored_without_crashing(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    add_entry(school_a)
    response = client.get(reverse("audit:list"), {"q": TOKEN, "from": "garbage", "to": "not-a-date"})
    assert response.status_code == 200
    assert len(response.context["page_obj"].object_list) == 1


def test_list_is_paginated(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    for number in range(28):
        add_entry(school_a, action=f"{TOKEN}.paged-{number}")
    response = client.get(reverse("audit:list"), {"q": TOKEN})
    page = response.context["page_obj"]
    assert page.paginator.count == 28 and len(page.object_list) == 25
    assert "Showing 1 to 25 of 28" in response.content.decode()
    second_page = client.get(reverse("audit:list"), {"q": TOKEN, "page": 2})
    assert len(second_page.context["page_obj"].object_list) == 3


def test_filters_survive_going_to_page_2(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    for number in range(28):
        add_entry(school_a, action=f"{TOKEN}.paged-{number}")
    response = client.get(reverse("audit:list"), {"q": TOKEN})
    html = response.content.decode()
    assert "q=t15a&amp;page=2" in html or "q=t15a&page=2" in html

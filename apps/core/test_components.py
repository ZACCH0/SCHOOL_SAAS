import pytest
from django import forms
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.views.defaults import permission_denied, server_error

@pytest.mark.django_db
def test_404_page_is_friendly(client):
    response = client.get("/no-such-page/")
    assert response.status_code == 404
    assert b"Page not found" in response.content

def test_403_page_explains_no_access():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    response = permission_denied(request, PermissionDenied())
    assert response.status_code == 403
    assert b"do not have access" in response.content

def test_500_page_does_not_crash():
    response = server_error(RequestFactory().get("/"))
    assert response.status_code == 500
    assert b"Something went wrong" in response.content

def test_status_chip_uses_kind_colours():
    ok = render_to_string("components/status_chip.html", {"kind": "ok", "label": "Active"})
    bad = render_to_string("components/status_chip.html", {"kind": "bad", "label": "Overdue"})
    assert "Active" in ok and "bg-green-100" in ok
    assert "Overdue" in bad and "bg-red-100" in bad

def test_empty_state_shows_action():
    html = render_to_string(
        "components/empty_state.html",
        {"title": "No students yet", "action_url": "/students/new/", "action_label": "Register student"},
    )
    assert "No students yet" in html
    assert 'href="/students/new/"' in html

def test_page_header_shows_title_and_action():
    html = render_to_string(
        "components/page_header.html",
        {"title": "Students", "action_url": "/x/", "action_label": "Add"},
    )
    assert "Students" in html and "Add" in html

def test_stat_card_warn_tone_uses_amber():
    html = render_to_string(
        "components/stat_card.html", {"label": "Owed", "value": "₦2,400,000", "tone": "warn"}
    )
    assert "₦2,400,000" in html and "text-amber-700" in html

def test_form_field_shows_label_and_error():
    class DemoForm(forms.Form):
        name = forms.CharField(label="Student name")

    form = DemoForm(data={"name": ""})
    form.is_valid()
    html = render_to_string("components/form_field.html", {"field": form["name"]})
    assert "Student name" in html
    assert "This field is required." in html

def test_pagination_hidden_for_a_single_page():
    page = Paginator(range(5), 10).page(1)
    html = render_to_string("components/pagination.html", {"page_obj": page})
    assert "Showing" not in html

def test_pagination_shows_range_and_links():
    page = Paginator(range(50), 10).page(2)
    html = render_to_string("components/pagination.html", {"page_obj": page})
    assert "Showing 11 to 20 of 50" in html
    assert "Previous" in html and "Next" in html
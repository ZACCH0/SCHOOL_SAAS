from datetime import date
from urllib.parse import urlencode

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import render

from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required

from .models import AuditLog

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)

PAGE_SIZE = 25


def _parse_date(raw):
    try:
        return date.fromisoformat(raw)
    except (TypeError, ValueError):
        return None


@manager_only
def audit_list(request):
    query = (request.GET.get("q") or "").strip()
    date_from = _parse_date(request.GET.get("from"))
    date_to = _parse_date(request.GET.get("to"))
    filters = Q()
    if query:
        filters &= (
            Q(actor_label__icontains=query)
            | Q(action__icontains=query)
            | Q(target_repr__icontains=query)
        )
    if date_from:
        filters &= Q(created_at__date__gte=date_from)
    if date_to:
        filters &= Q(created_at__date__lte=date_to)
    entries = AuditLog.objects.for_school(request.school).filter(filters)
    paginator = Paginator(entries, PAGE_SIZE)
    try:
        page_obj = paginator.page(request.GET.get("page", "1"))
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    params = {"q": query}
    if date_from:
        params["from"] = date_from.isoformat()
    if date_to:
        params["to"] = date_to.isoformat()
    base_query = urlencode(
        {key: value for key, value in params.items() if value}
    )
    return render(
        request,
        "audit/list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "date_from": date_from.isoformat() if date_from else "",
            "date_to": date_to.isoformat() if date_to else "",
            "base_query": base_query,
        },
    )

import secrets

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.permissions import REVIEWER_GROUP


@pytest.fixture(autouse=True)
def _clear_cache():
    # Throttle counters live in the cache; reset them so tests stay independent.
    cache.clear()
    yield


@pytest.fixture
def client():
    return APIClient()


def _client_for(username, groups=()):
    user = get_user_model().objects.create_user(username, password=secrets.token_urlsafe(12))
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    token = Token.objects.create(user=user)
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    api.user = user
    return api


@pytest.fixture
def reviewer_client(db):
    return _client_for("reviewer1", groups=[REVIEWER_GROUP])


@pytest.fixture
def member_client(db):
    return _client_for("member1")
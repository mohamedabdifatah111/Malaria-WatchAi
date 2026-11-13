from django.db.models import F, Q


def between(field, lo, hi):
    return Q(**{f"{field}__gte": lo, f"{field}__lte": hi})


def null_or_between(field, lo, hi):
    return Q(**{f"{field}__isnull": True}) | between(field, lo, hi)


def null_or_ordered(low, high):
    """low <= high whenever both are present."""
    return (
        Q(**{f"{low}__isnull": True})
        | Q(**{f"{high}__isnull": True})
        | Q(**{f"{low}__lte": F(high)})
    )
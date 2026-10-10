import uuid

from django.conf import settings
from django.core.cache import cache, caches
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from routing.best_effort import plan_best_effort
from routing.fallback_data import FallbackDataError, get_location_catalog
from routing.planning import plan
from routing.provider import Geoapify, ProviderError
from routing.repository import BestEffortRepository, StationRepository
from routing.serializers import RouteRequestSerializer


def create_provider():
    return Geoapify(settings.GEOAPIFY_API_KEY, cache=cache)


@api_view(["POST"])
def route_view(request):
    serializer = RouteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        with create_provider() as provider:
            route = provider.route(
                serializer.validated_data["start"], serializer.validated_data["finish"]
            )
        try:
            payload = plan(
                route, StationRepository(), cache, settings.STATION_CORRIDOR_MILES
            )
        except ProviderError as strict_error:
            if (
                strict_error.code != "insufficient_station_coverage"
                or not serializer.validated_data["allow_estimates"]
            ):
                raise
            try:
                catalog = get_location_catalog()
            except FallbackDataError as error:
                raise ProviderError(
                    "best_effort_data_unavailable",
                    str(error),
                    500,
                    details={
                        "planning_mode": "best_effort",
                        "status": "unavailable",
                        "fuel_feasibility": "unverified",
                        "strict_failure": strict_error.code,
                    },
                ) from None
            payload = plan_best_effort(
                route,
                BestEffortRepository(),
                cache,
                catalog,
                settings.STATION_CORRIDOR_MILES,
                settings.BEST_EFFORT_AREA_CORRIDOR_MILES,
            )
            payload = {**payload, "strict_coverage_failure": strict_error.details}
    except ProviderError as error:
        return Response(
            {
                "error": {
                    "code": error.code,
                    "message": error.message,
                    **({"details": error.details} if error.details is not None else {}),
                }
            },
            status=error.status,
        )
    except ValueError:
        return Response(
            {
                "error": {
                    "code": "invalid_route_geometry",
                    "message": "Route geometry could not be matched",
                }
            },
            status=502,
        )
    token = uuid.uuid4()
    caches["maps"].set(f"map:{token}", payload, 3600)
    return Response(
        {
            **payload,
            "map_url": request.build_absolute_uri(reverse("route-map", args=[token])),
        }
    )


def map_view(request, token):
    payload = caches["maps"].get(f"map:{token}")
    if payload is None:
        raise Http404("Map expired or unavailable")
    response = render(request, "routing/map.html", {"payload": payload})
    # OSM requires a browser Referer; Django's same-origin default suppresses it.
    # Share only the origin across sites, never the snapshot token in the URL.
    response["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

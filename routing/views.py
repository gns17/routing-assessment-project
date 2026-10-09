import uuid

from django.conf import settings
from django.core.cache import cache, caches
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from routing.planning import plan
from routing.provider import Geoapify, ProviderError
from routing.repository import StationRepository
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
        payload = plan(
            route, StationRepository(), cache, settings.STATION_CORRIDOR_MILES
        )
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
    return render(request, "routing/map.html", {"payload": payload})

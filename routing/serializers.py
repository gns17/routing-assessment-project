from rest_framework import serializers


class LocationString(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Expected a location string")
        value = super().to_internal_value(data)
        if any(ord(char) < 32 for char in value):
            raise serializers.ValidationError("Control characters are not allowed")
        return " ".join(value.split())


class StrictBoolean(serializers.BooleanField):
    def to_internal_value(self, data):
        if type(data) is not bool:
            raise serializers.ValidationError("Expected a JSON boolean")
        return data


class RouteRequestSerializer(serializers.Serializer):
    start = LocationString(max_length=300, allow_blank=False)
    finish = LocationString(max_length=300, allow_blank=False)
    allow_estimates = StrictBoolean(required=False, default=False)

    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - {
            "start",
            "finish",
            "allow_estimates",
        }:
            raise serializers.ValidationError(
                "Only start, finish and allow_estimates are supported"
            )
        return super().to_internal_value(data)

from config_loader import Route
from scheduler import _route_key


def test_route_key_distinguishes_routes_with_different_via():
    hkg_route = Route("CGO", "JFK", "economy", via="HKG", adults=2)
    tpe_route = Route("CGO", "JFK", "economy", via="TPE", adults=2)

    assert _route_key(hkg_route) != _route_key(tpe_route)


def test_route_key_distinguishes_routes_with_different_cabin_or_adults():
    economy_route = Route("CGO", "JFK", "economy", via="HKG", adults=2)
    business_route = Route("CGO", "JFK", "business", via="HKG", adults=2)
    one_adult_route = Route("CGO", "JFK", "economy", via="HKG", adults=1)

    assert _route_key(economy_route) != _route_key(business_route)
    assert _route_key(economy_route) != _route_key(one_adult_route)

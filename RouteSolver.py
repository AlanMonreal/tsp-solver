#!/usr/bin/env python3

import quiken
import arcgis
import error
# Exception imports
from os import getenv
from urllib.parse import urlparse


class NextMove():
    def __init__(self, tracking, move, unit):
        self.tracking = tracking if tracking else None
        self.move = move if move else None
        self.unit = unit if unit else None


class RouteSolver:
    def __init__(self):
        dbvars = urlparse(getenv('DBSTRING'))
        agId, agSecret = getenv('ARCGIS_AUTH').split(':')
        self.db = {
            'host': dbvars.hostname,
            'user': dbvars.username,
            'pass': dbvars.password,
            'name': dbvars.path[1:]
        }
        self.googleConfig = {
            'geocodeUrl': 'https://maps.googleapis.com/maps/api/geocode/json?',
            'directionsApi': getenv('DIRECTIONS_API'),
            'sourceCountry': 'MEX',
            'key': getenv('GOOGLE_API_KEY')
        }

    def run(self):
        try:
            self.geocode()
            self.generate_routes()
        except:
            errPayload = error.handleError()

    def geocode(self):
        user = quiken.get_user(self.db)
        addresses = quiken.get_addresses(self.db, user)
        if addresses:
            arcgis.geocode_func(addresses, self.googleConfig['geocodeUrl'],
                                self.googleConfig['key'])
            quiken.set_coordinates(self.db, addresses)

    def generate_routes(self):
        units = quiken.get_units(self.db)
        user = quiken.get_user(self.db)
        quiken.deactivate_unit(self.db, user)
        orders = quiken.get_orders(self.db, user)
        base_locations = quiken.get_bases(self.db)
        routes = self.solve_routes(orders, units, base_locations)
        del orders
        del units
        del base_locations
        if routes:
            quiken.delete_from_route(self.db, user)
            quiken.set_route(self.db, routes)
        del user

    def solve_routes(self, coordinates, units, base_location):
        print('solving {} routes'.format(len(coordinates)))
        routes = arcgis.process_vrp(self.googleConfig['directionsApi'],
                                    coordinates, units, base_location)
        return routes

    def set_unit_active(self, token):
        unit = quiken.user_from_token(self.db, token)
        response = quiken.set_active(self.db, unit)
        return response

    def validate_token(self, token):
        user = quiken.is_valid(self.db, token)
        return quiken.hasUnit(self.db, user) if user else False
        # if user is not False:
        #     return quiken.hasUnit(self.db, user)
        # else:
        #     return False

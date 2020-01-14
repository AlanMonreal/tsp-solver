#!/usr/bin/env python3

import arcgis
import error
# Exception imports
from os import getenv
from urllib.parse import urlparse
from math import radians, sin, cos, atan2, sqrt


class NextMove():
    def __init__(self, tracking, move, unit):
        self.tracking = tracking if tracking else None
        self.move = move if move else None
        self.unit = unit if unit else None


class RouteSolver:
    def __init__(self):
        dbvars = 1234
        # dbvars = urlparse(getenv('DBSTRING'))
        # agId, agSecret = getenv('ARCGIS_AUTH').split(':')
        # self.db = {
        #     'host': dbvars.hostname,
        #     'user': dbvars.username,
        #     'pass': dbvars.password,
        #     'name': dbvars.path[1:]
        # }
        # self.googleConfig = {
        #     'geocodeUrl': 'https://maps.googleapis.com/maps/api/geocode/json?',
        #     'directionsApi': getenv('DIRECTIONS_API'),
        #     'sourceCountry': 'MEX',
        #     'key': getenv('GOOGLE_API_KEY')
        # }

    def run(self, places):
        matrix = self.get_distance_matrix(places)
        for i in matrix:
            print(i)
        # routes = self.solve_routes(orders, units, base_locations)

    def solve_routes(self, coordinates, units, base_location):
        print('solving {} routes'.format(len(coordinates)))
        routes = arcgis.process_vrp(self.googleConfig['directionsApi'],
                                    coordinates, units, base_location)
        return routes

    def get_distance(o_lat, o_lng, d_lat, d_lng):
        E_RAD = 6371e3
        r_o_lat = radians(o_lat)
        r_d_lat = radians(d_lat)
        delta_lat = radians(d_lat - o_lat)
        delta_lng = radians(d_lng - o_lng)
        a = ((sin(delta_lat / 2) * sin(delta_lat / 2)) + cos(r_o_lat) *
             cos(r_d_lat) * (sin(delta_lng / 2) * sin(delta_lng / 2)))
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        d = E_RAD * c
        return d

    def get_distance_matrix(self, places):
        mtx = [[] for p in places]
        for i, plc in enumerate(places):
            e_lat = places[i]['lat']
            e_lng = places[i]['lng']
            for j, p in enumerate(places):
                lng = places[j]['lat']
                lat = places[j]['lng']
                if e_lat == lat and e_lng == lng:
                    mtx[i].append(99999999)
                mtx[i].append(self.get_distance(e_lat, e_lng, lat, lng))
        return mtx

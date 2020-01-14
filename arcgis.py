from urllib.request import urlopen
from urllib.parse import urlencode
from requests import get
from random import randint
from math import sqrt, ceil
from json import dumps, load
from os import getenv


class Route(object):
    __slots__ = 'track', 'kind', 'unit', 'sequence'

    def __init__(self, track, kind, unit, sequence):
        self.track = track
        self.kind = kind
        self.unit = unit
        self.sequence = sequence


pickupStatus = ['created', 'pickupassigned']


class ArcgisError(Exception):
    def __init__(self, system=None, message=None):
        self.system = system
        self.message = message


def geocode_func(addresses, url, key):
    for index, address in enumerate(addresses):
        print('line: ' + address.line + ' hood: ' + address.neighborhood +
              ' city: ' + address.city + ' postal: ' + address.postal)
        jointAddress = address.line + ', ' + address.neighborhood + ', ' + address.city + ', NL'
        postalCode = address.postal
        jointComponents = 'country:MX'
        reqData = {
            'address': jointAddress,
            'postal_code': postalCode,
            'components': jointComponents,
            'key': key
        }
        encData = url+'' + urlencode(reqData)
        with get(encData) as respData:
            respJson = respData.json()
            if not respJson['results']:
                geocodeRetry(address, jointAddress, jointComponents, url, key)
                continue  # TODO raise error
            address.warnings = None
            geometry = respJson['results'][0]['geometry']
            if geometry['location_type'] != 'ROOFTOP' and address.warnings is None:
                address.warnings = 'Aproximate location'
            address.latitude = round(geometry['location']['lat'], 8)
            address.longitude = round(geometry['location']['lng'], 8)
    return addresses


def geocodeRetry(address, jointAddress, components, url, key):
    reqData = {
        'address': jointAddress,
        'components': components,
        'key': key
    }
    fullUrl = url + urlencode(reqData)
    with get(fullUrl) as response:
        respJson = response.json()
        if not respJson['results']:
            print(fullUrl)
            address.latitude = round(25.588888, 8)
            address.longitude = round(-100.426888, 8)
            address.warnings = 'No geocode'
            # raise ArcgisError('Geocoding', respJson['status'])
            return address
        geometry = respJson['results'][0]['geometry']['location']
        address.latitude = round(geometry['lat'], 8)
        address.longitude = round(geometry['lng'], 8)
        address.warnings = 'Ambiguous address'
    return address


def process_vrp(url, orderLocations, units, baseLocations):
    finalOrder = []
    dftDepot = (baseLocations[0].y, baseLocations[0].x)
    shrtOList = trimOrders(orderLocations)
    ''' Maps API only acepts routes <= 25 waypoints
        (including origin and destination) '''
    if len(shrtOList) <= 23:
        waypointsStr = iterableWaypointsFormat(shrtOList)
        request = createRequest(url, dftDepot, dftDepot, waypointsStr)
        with urlopen(request, data=None) as respData:
            respJson = load(respData)
            wyporder = respJson["routes"][0]["waypoint_order"]
            for waypoint in wyporder:
                finalOrder.append(shrtOList[waypoint])
            # print(dumps(respJson))
    else:
        centNum = ceil(len(shrtOList) / 23)
        print('more than 23 points. orders: ' + str(len(shrtOList)) +
              ' centriole number: ' + str(centNum))
        totalTimes, totalRoutes, totalDistances = [], [], []

        ''' This process is repeated 3x to select the best outcome*
        *Outcome is heavily affected by K-means algorithm due to randomness'''
        for n in range(3):
            finalTime, tempRoute, finalDist = 0, [], 0
            clstData = kMeans(centNum, shrtOList)  # [[CENTRIOLE],[CLSTGEOCODES]]
            
            for j in range(centNum):
                orderedData, orderedCentriole = [], []

                ''' Decides to which area move next'''
                if j == 0:
                    cOrder = getCentrProx(dftDepot, clstData[0])
                elif j != 0 and j != (centNum - 1):
                    cOrder = getCentrProx(tempRoute[-1], clstData[0])

                ''' Selects waypoints to add in the request'''
                if j != (centNum - 1):
                    for i in cOrder:
                        orderedData.append(clstData[1][i])
                        orderedCentriole.append(clstData[0][i])
                    waypoints = iterableWaypointsFormat(orderedData[0])
                else:
                    waypoints = iterableWaypointsFormat(clstData[1][0])

                ''' Creates request (origin/destination point varies)'''
                if j == 0:
                    request = createRequest(url, dftDepot, orderedCentriole[0],
                                            waypoints)
                elif j == (centNum - 1):
                    cOrder = [0]
                    request = createRequest(url, tempRoute[-1], dftDepot,
                                            waypoints)
                else:
                    request = createRequest(url, tempRoute[-1], orderedCentriole[0],
                                            waypoints)

                with urlopen(request, data=None) as respData:
                    respJson = load(respData)
                    wyporder = respJson["routes"][0]["waypoint_order"]
                    wyplegs = respJson["routes"][0]["legs"]
                    for leg in wyplegs:
                        finalTime = finalTime + leg["duration"]["value"]
                        finalDist = finalDist + leg["distance"]["value"]
                    for waypoint in wyporder:
                        tempRoute.append(clstData[1][cOrder[0]][waypoint])
                    del clstData[1][cOrder[0]], clstData[0][cOrder[0]], cOrder[0]

            totalTimes.append(finalTime)
            totalDistances.append(finalDist)
            totalRoutes.append(tempRoute)
            # print('Total Times (sec) ', totalTimes)
            # print('Total Distances (m) ', totalDistances)
            del clstData
        for pos in totalRoutes[totalTimes.index(min(totalTimes))]:
            finalOrder.append(pos)
    routes = getOrder(finalOrder, orderLocations, units[0])
    return routes


def getOrder(routeOrder, guides, unit, index=1):
    routes = []
    for position in routeOrder:
        for guide in guides:
            if (guide.latitude, guide.longitude) == position:
                routes.append(Route(guide.track, 'pickup' if guide.kind in
                                    pickupStatus else 'deliver', unit.name,
                                    index))
                index += 1
    return routes


def createRequest(url, origin, destination, waypoints):
    request = 'origin={baseLat},{baseLng}&destination={destLat},{destLng}'\
              '&waypoints=optimize:true|{waypoints}&key={apiKey}'
    request = request.format(baseLat=origin[0], baseLng=origin[1],
                             destLat=destination[0], destLng=destination[1],
                             waypoints=waypoints, apiKey=getenv('GOOGLE_API_KEY'))
    request = url + request
    return request


def getCentrProx(baseLoc, comparisonItems):
    oList = []
    dist = calcEuclidian(baseLoc, comparisonItems)
    for i in range(len(dist)):
        oList.append(dist.index(min(dist)))
        dist[dist.index(min(dist))] = 99999
    return oList


def trimOrders(iterableObj):
    trimedList = []
    for point in iterableObj:
        tempList = (point.latitude, point.longitude)
        if tempList not in trimedList:
            trimedList.append(tempList)
    return trimedList


def kMeans(cNum, objSet):
    cList = []

    for i in range(cNum):
        cList.append(createRandomCentriole())

    for ite in range(10):
        assignedL = [[] for i in range(len(cList))]
        newCentList = [None for j in range(len(cList))]

        for gLocation in objSet:
            euc = calcEuclidian(gLocation, cList)
            assignedL[euc.index(min(euc))].append(gLocation)

        for index, centriole in enumerate(cList):
            if assignedL[index]:
                newCentList[index] = createNewCentriole(assignedL[index])
            else:
                newCentList[index] = cList[index]

        if newCentList == cList:
            break
        else:
            cList = newCentList.copy()

    assignedL = [[] for i in range(len(cList))]
    for gLocation in objSet:
        assigned = False
        euc = calcEuclidian(gLocation, cList)
        i = 0
        while not assigned:
            if i > len(euc):
                assigned: True
            if len(assignedL[euc.index(min(euc))]) < 23:
                assignedL[euc.index(min(euc))].append(gLocation)
                assigned = True
            else:
                euc[euc.index(min(euc))] = 9999
            i = i + 1
    response = [cList, assignedL]
    return response


def createRandomCentriole():
    ''' Creates random centriole in Mty Area '''
    x = ((createRandom(100424453, 100201206)/1000000)*(-1))
    y = (createRandom(25793848, 25632916)/1000000)
    return (y, x)


def createNewCentriole(itemList):
    x, y = 0, 0
    for element in itemList:
        y = y + element[0]
        x = x + element[1]
    y = y / len(itemList)
    x = x / len(itemList)
    return (y, x)


def calcEuclidian(val, centrioleL):
    return [sqrt((val[0] - point[0])**2 +
            (val[1] - point[1])**2) for point in centrioleL]


def iterableWaypointsFormat(iterable, fmt='{!s},{!s}', separator='|'):
    return separator.join(fmt.format(point[0], point[1]) for point in iterable)


def createRandom(maxN, minN):
    return randint(minN, maxN)

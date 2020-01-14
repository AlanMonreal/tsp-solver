from itertools import count
# from MySQLdb.constants import FIELD_TYPE
import MySQLdb


class Address(object):
    __slots__ = 'track', 'kind', 'line', 'neighborhood', 'city', 'postal', 'latitude', 'longitude', 'warnings'

    def __init__(self, track, kind, line, neighborhood, city, postal):
        self.track = track
        self.kind = kind  # TODO: Maybe change to boolean
        self.line = line
        self.neighborhood = neighborhood
        self.city = city
        self.postal = postal
        self.latitude = None
        self.longitude = None
        self.warnings = None

    def __str__(self):
        return 'track: %s, kind: %s, warnings: %s'(self.track, self.kind)


class Order(object):
    __slots__ = 'track', 'kind', 'service', 'latitude', 'longitude', 'unit'

    def __init__(self, track, kind, service, latitude, longitude, unit):
        self.track = track
        self.kind = kind
        self.service = service
        self.latitude = float(latitude) if latitude else None
        self.longitude = float(longitude) if longitude else None
        self.unit = unit if unit else None

    def __str__(self):
        return 'track: %s, kind: %s'(self.track, self.kind)


class Unit(object):
    __slots__ = 'name', 'base', 'capacity', 'specialty'

    def __init__(self, name, base, capacity, specialty=None):
        self.name = name
        self.base = base
        self.capacity = capacity
        self.specialty = specialty if specialty else None


class BaseLocation(object):
    __slots__ = 'name', 'y', 'x'

    def __init__(self, name, y, x):
        self.name = name
        self.y = y
        self.x = x


shipmentStatus = {
    'pickup': 2,
    'store': 3,  # Package arrived to station
    'load': 4,  # Package assigned and loaded to unit
    'deliver': 5,  # <-- TEST
    'error': 7,
    'information': 7
}


def get_addresses(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = '''SELECT tracking_number, CONCAT(IFNULL(origin_street,''), ' ',
          IFNULL(origin_ext_number,'')) AS line, IFNULL(origin_district, '') AS
          neighborhood, origin_city AS city, origin_postal_code AS postal,
          'pickup' AS kind FROM shipment_guides WHERE (origin_latitude is NULL
          AND origin_longitude is NULL AND assigned_to = %s AND status_id != 5
          AND status_id != 8)
          UNION SELECT tracking_number, CONCAT(IFNULL(destination_street,''),
          ' ', IFNULL(destination_ext_number,'')), IFNULL(destination_district,
          ''), destination_city, destination_postal_code, 'delivery'
          FROM shipment_guides WHERE (destination_latitude is NULL AND
          destination_longitude is NULL AND assigned_to = %s AND status_id != 5
          AND status_id != 8)'''
    dbcur.execute(sql, (user, user)) 
    locationData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    addresses = []
    for locInfo in locationData:
        addresses.append(Address(locInfo[0], locInfo[5], locInfo[1],
                                 locInfo[2], locInfo[3], locInfo[4]))
    return addresses


def set_coordinates(dbvars, addresses):
    updateData = []
    for address in addresses:
        updateData.append((address.kind, address.latitude, address.longitude,
                           address.latitude, address.longitude,
                           address.warnings, address.warnings, address.track))
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    # TODO: refactor sql script to pass lat & lng just once
    sql = '''UPDATE shipment_guides SET
        origin_latitude = if((@kind:=%s) = 'pickup', %s, origin_latitude),
        origin_longitude = if(@kind = 'pickup', %s, origin_longitude),
        destination_latitude = if(@kind = 'delivery', %s, destination_latitude),
        destination_longitude = if(@kind = 'delivery', %s, destination_longitude),
        origin_warnings = if(@kind = 'pickup', %s, origin_warnings),
        destination_warnings = if(@kind = 'delivery', %s, destination_warnings)
        WHERE tracking_number=%s'''
    dbcur.executemany(sql, updateData)
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def get_orders(dbvars, assigned):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    createdStatus = 1, 9
    pickedupStatus = 2,
    stationStatus = 3, 10
    loadedStatus = 4,
    sql = '''
        SELECT tracking_number AS track, 'created' AS kind, service_id AS
        service, origin_latitude AS latitude, origin_longitude AS longitude,
        null AS unit
        FROM shipment_guides WHERE origin_latitude IS NOT NULL AND
        origin_longitude IS NOT NULL AND status_id IN ({}) #Status_id = 1 o 9
        AND assigned_to = %s
        UNION SELECT tracking_number, 'picked', service_id, origin_latitude,
        origin_longitude, u.name
        FROM shipment_guides s LEFT JOIN unit_shipments o on s.tracking_number
        = o.shipment_id LEFT JOIN units u on  o.unit_id=u.id
        WHERE origin_latitude IS NOT NULL AND origin_longitude IS NOT NULL AND
        status_id IN ({}) AND assigned_to = %s
        UNION SELECT tracking_number, 'store', service_id, destination_latitude,
        destination_longitude, null
        FROM shipment_guides WHERE destination_latitude IS NOT NULL AND
        destination_longitude IS NOT NULL AND status_id IN ({})
        AND assigned_to = %s
        UNION SELECT tracking_number, 'loaded', service_id, destination_latitude,
        destination_longitude, u.name
        FROM shipment_guides s LEFT JOIN units u on s.assigned_to=u.user_id
        WHERE destination_latitude IS NOT NULL AND destination_longitude IS NOT
        NULL AND status_id IN ({})
        AND assigned_to = %s
    '''
    sql = sql.format(','.join(['%s']*len(createdStatus)), ','.join(['%s']*len(pickedupStatus)),
                     ','.join(['%s']*len(stationStatus)), ','.join(['%s']*len(loadedStatus)))
    dbcur.execute(sql, createdStatus + assigned + pickedupStatus + assigned +
                  stationStatus + assigned + loadedStatus + assigned)
    locationData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    orders = []
    for locInfo in locationData:
        orders.append(Order(locInfo[0], locInfo[1], locInfo[2], locInfo[3],
                            locInfo[4], locInfo[5]))
    return orders


def get_units(dbvars):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT u.name, bl.name, u.capacity, u.specialties AS specialty '\
          'FROM units AS u LEFT JOIN base_locations AS bl ON u.base_'\
          'location_id = bl.id WHERE u.active=1'
    dbcur.execute(sql)
    unitData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    units = []
    for unitInfo in unitData:
        units.append(Unit(unitInfo[0], unitInfo[1], unitInfo[2]))
    return units


def get_bases(dbvars):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    sql = 'SELECT name, latitude, longitude FROM base_locations WHERE active=true'
    dbcur.execute(sql)
    baseLocData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    baseLocations = []
    for baseLoc in baseLocData:
        baseLocations.append(BaseLocation(baseLoc[0], float(baseLoc[1]),
                                          float(baseLoc[2])))
    return baseLocations


def set_route(dbvars, routes):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    data = []
    for route in routes:
        data.append((route.track,))
    sql = 'DELETE FROM unit_shipments WHERE shipment_id = %s'
    dbcur.executemany(sql, data)
    data.clear()
    for route in routes:
        data.append((route.track, route.unit, route.kind, route.sequence))
    sql = 'INSERT INTO unit_shipments(shipment_id,unit_id,kind,sequence) '\
          'VALUES (%s,(SELECT id FROM units WHERE name=%s),%s,%s)'
    dbcur.executemany(sql, data)
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def user_from_token(dbvars, token):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    regs = dbcur.execute('SELECT id FROM users WHERE app_token = %s', (token,))
    unitData = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return unitData[0][0] if regs else None


def get_user(dbvars):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT user_id FROM units WHERE active = true')
    userData = dbcur.fetchall()
    sUser = userData[0]
    dbcur.close()
    dbconn.close()
    return sUser


def deactivate_unit(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('UPDATE units SET active = false WHERE user_id = %s', user)
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def delete_from_route(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT id FROM units WHERE user_id = %s', user)
    unit = dbcur.fetchall()
    unit = unit[0]
    dbcur.execute('DELETE FROM unit_shipments WHERE unit_id = %s', unit)
    dbconn.commit()
    dbcur.close()
    dbconn.close()


def set_active(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('UPDATE units SET active = 1 WHERE user_id = %s', (user,))
    dbconn.commit()
    dbcur.close()
    dbconn.close()
    return 'ok'


def is_valid(dbvars, token):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT id FROM users WHERE app_token = %s', (token,))
    data = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return data[0] if data else False


def hasUnit(dbvars, user):
    dbconn = MySQLdb.connect(host=dbvars['host'], user=dbvars['user'],
                             passwd=dbvars['pass'], db=dbvars['name'])
    dbcur = dbconn.cursor()
    dbcur.execute('SELECT id FROM units WHERE user_id = %s', (user,))
    data = dbcur.fetchall()
    dbcur.close()
    dbconn.close()
    return True if data else False

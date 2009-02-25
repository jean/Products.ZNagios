# Copyright (c) 2004-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id: __init__.py 5611 2008-02-29 09:43:31Z ctheune $
#
# ZNagios, (C) gocept gmbh & co. kg 2004-2008

import DateTime
import OFS.Application
import Zope2.App.startup
import time


# Delta used for taking delta measurements and normalization
MUNIN_TIME_DELTA = 60*5


def get_refcount(self):
    """Determine the total amount of object reference counts."""
    all = self.Control_Panel.DebugInfo.refcount()
    size = 0
    for v, n in all:
        size += v
    return size


def get_activity(db):
    now = float(DateTime.DateTime())
    request = dict(chart_start=now-MUNIN_TIME_DELTA,
                   chart_end=now)
    return db.getActivityChartData(200, request)


def nagios(self):
    """A method to allow nagios checks with a bit more information.

    Returns a dictionary line-by-line with the following keys:

    """
    result = ""

    # Uptime
    result += "uptime: %s\n" % self.Control_Panel.process_time().strip()

    # Database size
    size = self.Control_Panel.db_size()
    if size[-1] == "k":
        size = float(size[:-1]) * 1024
    else:
        size = float(size[:-1]) * 1048576
    result += "database: %s\n" % int(size)

    # references
    size = get_refcount(self)
    result += "references: %s\n" % size

    # error_log 
    errors = self.error_log._getLog()

    i = 0
    for error in errors:
        result += "error%i: %s, %s, %s, %s, %s\n" % (i, error['type'], error['value'],
                    error['username'], error['userid'], error['url'])
        i += 1
    return result


def munin(self):
    """Return munin-compatible statistic data."""
    data = {}

    # Uptime
    # ... in seconds since startup
    data['uptime'] = int(time.time())-self.Control_Panel.process_start

    # Reference counts
    # ... total number of objects referenced
    data['refcount-total'] = get_refcount(self)

    main_db = self.Control_Panel.Database['main']
    # Database size
    # ... in bytes
    data['db-bytes'] = main_db._getDB()._storage.getSize()
    # ... in number of objects
    data['db-objects'] = main_db.database_size()

    # Cache information (whole process)
    # ... total number of objects in all caches
    data['db-cache-total-size'] = main_db.cache_length()

    # Cache information (per connection/thread)
    # ... target size
    data['db-cache-target-size'] = main_db.cache_size()
    for i, connection in enumerate(main_db.cache_detail_length()):
        # ... active objects for the connect
        data['db-cache-conn%s-active-objects' % i] = connection['ngsize']
        # ... total objects (active and inactive) for the connection
        data['db-cache-conn%s-total-objects' % i] = connection['size']

    # Activity information
    # measured for the last 5 minutes, normalized per second
    activity = get_activity(main_db)
    # ... loads per second in the last 5 minutes
    data['db-loads'] = activity['total_load_count'] / MUNIN_TIME_DELTA
    # ... stores per second in the last 5 minutes
    data['db-stores'] = activity['total_store_count'] / MUNIN_TIME_DELTA
    # ... number of connections to the DB per second in the last 5 minutes
    data['db-connections'] = activity['total_connections'] / MUNIN_TIME_DELTA

    # Error information
    # ... number of errors in the log
    data['errors-total'] = len(self.error_log._getLog())
    # ... number of all conflict errors since startup
    data['conflicts-total'] = Zope2.App.startup.conflict_errors
    # ... number of all unresolved conflict errors since startup
    data['conflicts-unresolved'] = Zope2.App.startup.unresolved_conflict_errors

    # RRDTool: everything's a float
    for key, value in data.items():
        data[key] = float(value)

    self.REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
    return "\n".join("%s: %s"  % (k, v) for k, v in data.items())


OFS.Application.Application.nagios = nagios
OFS.Application.Application.nagios__roles__ = None


OFS.Application.Application.munin = munin
OFS.Application.Application.munin__roles = None

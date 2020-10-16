# TOD planning templates toolkit
# Alex Bell, Renaissance Planning
# 2017


import arcpy
import uuid
from . import HandyGP
import numpy as np
from . import SmartAlloc as SA
import math
import pandas as pd

# globals
global METERS_PER_MILE, TECH_DEFAULTS, STATION_TYPE_DEFAULTS

METERS_PER_MILE = 1609.3472186944375

TECH_DEFAULTS = {
    "BRT": {
        "res_target": 2500,
        "job_target": 10000,
        "hot_target": 300,
        "spd_target": 15,
        "spacing_sh": 2640,
        "spacing_ln": 6600,
    },
    "LRT": {
        "res_target": 3000,
        "job_target": 12000,
        "hot_target": 400,
        "spd_target": 23,
        "spacing_sh": 3960,
        "spacing_ln": 10560,
    },
    "HR": {
        "res_target": 4000,
        "job_target": 15000,
        "hot_target": 500,
        "spd_target": 30,
        "spacing_sh": 5280,
        "spacing_ln": 15840,
    },
}
# default station types (w/ specs)
STATION_TYPE_DEFAULTS = {
    # "Neighborhood - BRT": {
    #     "res_target": 1500,
    #     "job_target": 1500,
    #     "hot_target": 0,
    #     "min_hot_sz": 40,
    #     "buff_area": 2640,
    #     "dens_grad": "Default Density",
    #     "res_grad": "Default Res Mix",
    # },
    # "Neighborhood - LRT": {
    #     "res_target": 2000,
    #     "job_target": 2000,
    #     "hot_target": 0,
    #     "min_hot_sz": 40,
    #     "buff_area": 2640,
    #     "dens_grad": "Default Density",
    #     "res_grad": "Default Res Mix",
    # },
    # "Neighborhood - HR": {
    #     "res_target": 3000,
    #     "job_target": 3000,
    #     "hot_target": 150,
    #     "min_hot_sz": 50,
    #     "buff_area": 2640,
    #     "dens_grad": "Default Density",
    #     "res_grad": "Default Res Mix",
    # },
    "Community - BRT": {
        "res_target": 2000,
        "job_target": 6000,
        "hot_target": 200,
        "min_hot_sz": 50,
        "buff_area": 2640,
        "dens_grad": "Default Density",
        "res_grad": "Default Res Mix",
    },
    # "Community - LRT": {
    #     "res_target": 4000,
    #     "job_target": 12000,
    #     "hot_target": 400,
    #     "min_hot_sz": 60,
    #     "buff_area": 2640,
    #     "dens_grad": "Default Density",
    #     "res_grad": "Default Res Mix",
    # },
    # "Community - HR": {
    #     "res_target": 6000,
    #     "job_target": 18000,
    #     "hot_target": 600,
    #     "min_hot_sz": 80,
    #     "buff_area": 2640,
    #     "dens_grad": "Default Density",
    #     "res_grad": "Default Res Mix",
    # },
    "Regional - BRT": {
        "res_target": 5000,
        "job_target": 30000,
        "hot_target": 900,
        "min_hot_sz": 100,
        "buff_area": 2640,
        "dens_grad": "Default Density",
        "res_grad": "Default Res Mix",
    },
    # "Regional - LRT": {
    #     "res_target": 7500,
    #     "job_target": 45000,
    #     "hot_target": 1500,
    #     "min_hot_sz": 150,
    #     "buff_area": 2640,
    #     "dens_grad": "Default Density",
    #     "res_grad": "Default Res Mix",
    # },
    # "Regional - HR": {
    #     "res_target": 12500,
    #     "job_target": 75000,
    #     "hot_target": 2000,
    #     "min_hot_sz": 150,
    #     "buff_area": 2640,
    #     "dens_grad": "Default Density",
    #     "res_grad": "Default Res Mix",
    # },
    "Downtown Employment - BRT": {
            "res_target": 8000,
            "job_target": 18000,
            "hot_target": 500,
            "min_hot_sz": 100,
            "buff_area": 2640,
            "dens_grad": "Downtown Employment Density",
            "res_grad": "Downtown Employment Mix",
        },
    "Downtown Neighborhood - BRT": {
        "res_target": 8000,
        "job_target": 4000,
        "hot_target": 200,
        "min_hot_sz": 50,
        "buff_area": 2640,
        "dens_grad": "Downtown Neighborhood Density",
        "res_grad": "Downtown Neighborhood Mix",
    },
    "Employment Hub - BRT": {
        "res_target": 3000,
        "job_target": 12000,
        "hot_target": 500,
        "min_hot_sz": 100,
        "buff_area": 2640,
        "dens_grad": "Employment Hub Density",
        "res_grad": "Employment Hub Mix",
    },
    "Town Center - BRT": {
        "res_target": 4000,
        "job_target": 4000,
        "hot_target": 200,
        "min_hot_sz": 50,
        "buff_area": 2640,
        "dens_grad": "Town Center Density",
        "res_grad": "Town Center Mix",
    },
    "Neighborhood - BRT": {
        "res_target": 3500,
        "job_target": 1500,
        "hot_target": 0,
        "min_hot_sz": 40,
        "buff_area": 2640,
        "dens_grad": "Neighborhood Density",
        "res_grad": "Neighborhood Mix",
    },
}

GRADIENT_DEFAULTS = {
    "Default Density": {
        "from_val": [0, 500, 1000, 1500, 2000, 2500],
        "to_val": [500, 1000, 1500, 2000, 2500, 5280],
        "weight": [100, 85, 70, 55, 40, 25],
    },
    "Default Res Mix": {
        "from_val": [0, 660, 1320, 2000],
        "to_val": [660, 1320, 2000, 5280],
        "weight": [25, 50, 75, 100],
    },
    "Downtown Employment Mix": {
        "from_val": [0, 660, 1320, 2000],
        "to_val": [660, 1320, 2000, 5280],
        "weight": [0, 15, 50, 100],
    },
    "Downtown Neighborhood Mix": {
        "from_val": [0, 660, 1320, 2000],
        "to_val": [660, 1320, 2000, 5280],
        "weight": [55, 70, 85, 100],
    },
    "Employment Hub Mix": {
        "from_val": [0, 660, 1320, 2000],
        "to_val": [660, 1320, 2000, 5280],
        "weight": [10, 35, 65, 100],
    },
    "Town Center Mix": {
        "from_val": [0, 660, 1320, 2000],
        "to_val": [660, 1320, 2000, 5280],
        "weight": [25, 50, 75, 100],
    },
    "Neighborhood Mix": {
        "from_val": [0, 660, 1320, 2000],
        "to_val": [660, 1320, 2000, 5280],
        "weight": [70, 80, 90, 100],
    },
    "Downtown Employment Density": {
        "from_val": [0, 500, 1000, 1500, 2000, 2500],
        "to_val": [500, 1000, 1500, 2000, 2500, 5280],
        "weight": [100, 95, 85, 75, 65, 50],
    },
    "Downtown Neighborhood Density": {
        "from_val": [0, 500, 1000, 1500, 2000, 2500],
        "to_val": [500, 1000, 1500, 2000, 2500, 5280],
        "weight": [100, 90, 75, 65, 55, 35],
    },
    "Employment Hub Density": {
        "from_val": [0, 500, 1000, 1500, 2000, 2500],
        "to_val": [500, 1000, 1500, 2000, 2500, 5280],
        "weight": [100, 85, 70, 55, 30, 10],
    },
    "Town Center Density": {
        "from_val": [0, 500, 1000, 1500, 2000, 2500],
        "to_val": [500, 1000, 1500, 2000, 2500, 5280],
        "weight": [100, 80, 65, 45, 40, 25],
    },
    "Neighborhood Density": {
        "from_val": [0, 500, 1000, 1500, 2000, 2500],
        "to_val": [500, 1000, 1500, 2000, 2500, 5280],
        "weight": [100, 75, 55, 35, 25, 5],
    },

}


# TOD TEMPLATE CLASSES
# ----------------------------------------------------------------------------------------------
class TransitTech(object):
    """Key questions about a transit technology:
        - what activity levels are neeeded to support the transit improvement
            (per linear infra. mile)?
        - what is the target operating speed?
        - how far apart should stations be placed?
    """

    def __init__(
            self,
            name,
            res_target,
            job_target,
            hotel_target,
            speed_target,
            spacing_short,
            spacing_long,
    ):
        self.name = name
        self.res_target = res_target
        self.job_target = job_target
        self.hotel_target = hotel_target
        ###
        self.speed_target = speed_target
        self.spacing_short = spacing_short
        self.spacing_long = spacing_long


class StationType(object):
    """key questions about station types
        - what is the total activity (DUs, Jobs,etc.) needed for the station type?
        - what mix of activities is typical for the station type?
        - what is the density gradient for the station type?
        - what is the res mix gradient for the station type?
    """

    def __init__(
            self,
            name,
            res_target,
            job_target,
            hotel_target,
            min_hotel_size=50,
            buffer_area=None,
            density_gradient=None,
            res_mix_gradient=None,
    ):
        self.name = name
        self.res_target = res_target
        self.job_target = job_target
        self.hotel_target = hotel_target
        self.min_hotel_size = min_hotel_size
        self.buffer_area = buffer_area
        self.density_gradient = density_gradient
        self.res_mix_gradient = res_mix_gradient

    def totalActivityTarget(self):
        return sum([self.res_target, self.job_target, self.hotel_target])


class Gradient(object):
    def __init__(self):
        self.value_ranges = []

    def addValueRange(self, from_val, to_val, weight):
        value_range = (from_val, to_val, weight)
        self.value_ranges.append(value_range)
        self.value_ranges.sort()

    def interpWeight(self, in_value):
        weight = 0
        for value_range in self.value_ranges:
            if value_range[0] <= in_value <= value_range[1]:
                weight = value_range[2]
        return weight


class Corridor(object):
    def __init__(self, technology, stations=[], sr=None):
        """
        technology = tecnology object
        stations = list of station objects
        """
        self.technology = technology
        self.sr = sr
        self.stations = []
        for station in stations:
            self.insertStation(station, station.order)
        self.setLengthFromStations()
        self.setTargets()
        self.station_res = 0.0
        self.station_job = 0.0
        self.station_hotel = 0.0

    def setTargets(self):
        self.res_target = self.length * self.technology.res_target
        self.job_target = self.length * self.technology.job_target
        self.hotel_target = self.length * self.technology.hotel_target
        self.speed_target = self.technology.speed_target
        self.spacing_short = self.technology.spacing_short
        self.spacing_long = self.technology.spacing_long

    def setTechnologyDict(self, technology):
        self.technology = technology
        self.setTargets()

    def setLength(self, length):
        self.length = length
        self.setTargets()

    def setLengthFromStations(self):
        if not self.stations:
            self.setLength(0.0)
        else:
            length = 0.0
            prev_point = self.stations[0].shape
            for station in self.stations:
                this_point = station.shape
                length += HandyGP._getDistanceBetweenPoints(
                    prev_point, this_point, self.sr
                )
                prev_point = this_point
            try:
                meters_per_unit = self.sr.metersPerUnit
            except AttributeError:
                # assume meters
                meters_per_unit = 1.00
            length_in_meters = length * meters_per_unit
            length_in_miles = length_in_meters / METERS_PER_MILE
            self.setLength(length_in_miles)

    def insertStation(self, station_obj, order=-1):
        self._insertStation(station_obj, order)
        self.setLengthFromStations()

    def _insertStation(self, station_obj, order=-1):
        if not self.stations:
            station_obj.order = 1
            self.stations.append(station_obj)
            return
        if order == -1:
            max_order = self.stations[-1].order
            station_obj.order = max_order + 1
            self.stations.append(station_obj)
            return
        else:
            station_obj.order = order
            idx = 0
            for station in self.stations:
                if station.order >= order:
                    break
                idx += 1
            for station in self.stations[idx:]:
                station.order += 1
            self.stations.insert(idx, station_obj)
            return

    def removeStation(self, station_name):
        _removeElement(self.stations_dict, station_name)

    def _stationsToDict(self):
        keys = [station.name for station in self.stations]
        return dict(list(zip(keys, self.stations)))

    def adjustStationActivitiesToTargets(self):
        self.summarizeStationActivities()
        res_factor = self.res_target / float(self.station_res)
        job_factor = self.job_target / float(self.station_job)
        hotel_factor = self.hotel_target / float(self.station_hotel)
        for station in self.stations:
            if res_factor > 1.0:
                for dev_area in station.dev_areas:
                    dev_area.res_activity *= res_factor
            if job_factor > 1.0:
                for dev_area in station.dev_areas:
                    dev_area.job_activity *= job_factor
            if hotel_factor > 1.0:
                for dev_area in station.dev_areas:
                    dev_area.hotel_activity *= hotel_factor
            station._updateTotalActivities()

    def evaluateSpacingAndSpeed(self):
        # use stations to determine speeds by station-to-station leg,
        # average station spacing, etc.
        pass

    def summarizeStationActivities(self):
        self.station_res = sum([station.res_activity for station in self.stations])
        self.station_job = sum([station.job_activity for station in self.stations])
        self.station_hotel = sum([station.hotel_activity for station in self.stations])

    def _convertToRow(self):
        self.summarizeStationActivities()
        return (self.station_res, self.station_job, self.station_hotel)


class Station(object):
    def __init__(self, name, station_type, order, shape, sr):
        self.name = name
        self.station_type = station_type
        self.order = order
        self.shape = shape
        self.sr = sr
        self.dev_areas = []
        self.res_activity = 0.0
        self.job_activity = 0.0
        self.hotel_activity = 0.0

    def addDevArea(self, dev_area_obj):
        self.dev_areas.append(dev_area_obj)

    def _prepareDevAreas(self):
        for dev_area in self.dev_areas:
            point_1 = dev_area.shape.centroid
            dev_area.dist_to_station = HandyGP._getDistanceBetweenPoints(
                point_1, self.shape, self.sr
            )
            dev_area.dens_weight = 1.0
            dev_area.res_mix_weight = 1.0
            if self.station_type.density_gradient:
                dev_area.density_weight = self.station_type.density_gradient.interpWeight(
                    dev_area.dist_to_station
                )
            if self.station_type.res_mix_gradient:
                dev_area.res_mix_weight = self.station_type.res_mix_gradient.interpWeight(
                    dev_area.dist_to_station
                )

    def distributeTargetsToDevAreas(self, use_suitability=False):
        # prepare development areas
        self._prepareDevAreas()
        # focus on total activity
        total_target = self.station_type.totalActivityTarget()
        dist_array = _devAreasToNpArray(
            self.dev_areas,
            "total_activity",
            "density_weight",
            use_suitability=use_suitability,
        )
        dist_array = _distribute(
            total_target, dist_array, "total_activity", "density_weight"
        )
        _NpArrayToDevAreas(self, dist_array, "total_activity")
        # focus on res activity
        res_target = self.station_type.res_target
        dist_array = _devAreasToNpArray(
            self.dev_areas,
            "res_activity",
            "res_mix_weight",
            control_attr="total_activity",
        )
        dist_array = _distribute(
            res_target,
            dist_array,
            "res_activity",
            "res_mix_weight",
            control_attr="total_activity",
        )
        _NpArrayToDevAreas(self, dist_array, "res_activity")
        # focus on non_res activity
        for dev_area in self.dev_areas:
            dev_area.nonres_activity = dev_area.total_activity - dev_area.res_activity
        # distribute hotel rooms
        hotel_target = self.station_type.hotel_target
        dist_array = _devAreasToNpArray(
            self.dev_areas,
            "hotel_activity",
            "nonres_activity",
            control_attr="nonres_activity",
        )
        dist_array = _allocate(
            hotel_target,
            dist_array,
            "hotel_activity",
            "nonres_activity",
            control_attr="nonres_activity",
            min_value=self.station_type.min_hotel_size,
        )
        _NpArrayToDevAreas(self, dist_array, "hotel_activity")
        # distribute jobs
        for dev_area in self.dev_areas:
            dev_area.job_activity = dev_area.nonres_activity - dev_area.hotel_activity
        # update station totals
        self.summarizeDevAreaActivities()

    def _updateTotalActivities(self):
        for dev_area in self.dev_areas:
            dev_area.nonres_activity = dev_area.hotel_activity + dev_area.job_activity
            dev_area.total_activity = dev_area.res_activity + dev_area.nonres_activity

    def summarizeDevAreaActivities(self):
        self.res_activity = sum([dev_area.res_activity for dev_area in self.dev_areas])
        self.job_activity = sum([dev_area.job_activity for dev_area in self.dev_areas])
        self.hotel_activity = sum(
            [dev_area.hotel_activity for dev_area in self.dev_areas]
        )

    def _convertToRow(self, name_type="TEXT"):
        self.summarizeDevAreaActivities()
        if name_type == "TEXT":
            out_row = [str(self.name)]
        elif name_type in ["LONG", "SHORT"]:
            out_row = [int(self.name)]
        else:
            out_row = [float(self.name)]
        out_row += [self.res_activity, self.job_activity, self.hotel_activity]
        return tuple(out_row)


class DevArea(object):
    def __init__(
            self,
            name,
            shape,
            sr,
            existing_res_activity=0.0,
            existing_job_activity=0.0,
            existing_hotel_activity=0.0,
            area=1.0,
    ):
        self.area = area
        self.name = str(name)
        self.shape = shape
        self.sr = sr
        self.existing_res_activity = existing_res_activity
        self.existing_job_activity = existing_job_activity
        self.existing_hotel_activity = existing_hotel_activity
        self.dist_to_station = 0.0
        self.density_weight = 0.0
        self.res_mix_weight = 0.0
        self.total_activity = 0.0
        self.res_activity = 0.0
        self.nonres_activity = 0.0
        self.job_activity = 0.0
        self.hotel_activity = 0.0
        self.suitability_score = None

    def __setattr__(self, name, value):
        if name == "density_weight":
            super(DevArea, self).__setattr__(name, value * self.area)
        else:
            super(DevArea, self).__setattr__(name, value)

    def setSuitability(self, suitability_score):
        self.suitability_score = suitability_score

    def _convertToRow(self, name_type="TEXT"):
        if name_type == "TEXT":
            out_row = [str(self.name)]
        elif name_type in ["LONG", "SHORT"]:
            out_row = [int(self.name)]
        else:
            out_row = [float(self.name)]

        out_row += [
            self.dist_to_station,
            self.total_activity,
            self.res_activity,
            self.nonres_activity,
            self.job_activity,
            self.hotel_activity,
        ]
        return tuple(out_row)


# TOD CLASS HELPER FUNCTIONS
# ----------------------------------------------------------------------------------------------
def _distribute(total, array, sum_attr, weight_attr, control_attr=None, min_value=None):
    if control_attr:
        control_attr = "xx__CONTROL__xx"
    weight_total = np.sum(array[weight_attr])
    sum_total = np.sum(array[sum_attr])
    dist_total = total - sum_total
    array[weight_attr] = array[weight_attr] / weight_total
    for row in array:
        if row[weight_attr] > 0.0:
            val = row[weight_attr] * dist_total
            if control_attr:
                if val >= row[control_attr] - row[sum_attr]:
                    val = row[control_attr] - row[sum_attr]
                    row[weight_attr] = 0.0
            if min_value:
                if val < min_value:
                    val = 0
                    row[weight_attr] = 0.0
            row[sum_attr] += math.ceil(val)
    sum_total = np.sum(array[sum_attr])
    weight_total_check = np.sum(array[weight_attr])
    if sum_total < total and weight_total_check > 0.0:
        return _distribute(total, array, sum_attr, weight_attr, control_attr)
    else:
        return array


def _allocate(total, array, sum_attr, weight_attr, control_attr=None, min_value=1.0):
    if control_attr:
        control_attr = "xx__CONTROL__xx"
    for row in array:
        if row[control_attr] < min_value:
            row[weight_attr] = 0.0

    valid_alloc = 0.0
    while valid_alloc < total:
        # choose a row for allocation
        selected_row = SA._selectRandomRowFromArray(array, [weight_attr])
        selected_row[sum_attr] += 1
        selected_row[control_attr] -= 1
        # check the allocated number of meeting the min_value criterion
        valid_alloc = np.sum(array[np.where(array[sum_attr] >= min_value)][sum_attr])

    # zero out rows that didn't meet the minimum
    for row in array:
        if row[sum_attr] < min_value:
            row[sum_attr] = 0.0
    return array


def _devAreasToNpArray(
        dev_areas, sum_attr, weight_attr, control_attr=None, use_suitability=False
):
    rows = []
    for dev_area in dev_areas:
        name_val = dev_area.name
        sum_val = dev_area.__dict__[sum_attr]
        if use_suitability:
            weight_val = dev_area.__dict__[weight_attr] * dev_area.suitability_score
        else:
            weight_val = dev_area.__dict__[weight_attr]
        row = [name_val, sum_val, weight_val]
        if control_attr:
            control_val = dev_area.__dict__[control_attr]
            row.append(control_val)
        rows.append(tuple(row))
    ##    if control_attr:
    ##        rows = [(dev_area.name, dev_area.__dict__[sum_attr], dev_area.__dict__[weight_attr],
    ##                 dev_area.__dict__[control_attr]) for dev_area in dev_areas]
    ##    else:
    ##        rows = [(dev_area.name, dev_area.__dict__[sum_attr], dev_area.__dict__[weight_attr])
    ##                 for dev_area in dev_areas]
    dt_list = [("NAME", "|S50"), (sum_attr, "<f8"), (weight_attr, "<f8")]
    if control_attr:
        dt_list.append(("xx__CONTROL__xx", "<f8"))
    array = np.array(rows, dtype=np.dtype(dt_list))
    return array


def _NpArrayToDevAreas(station_obj, array, sum_attr):
    keys = [dev_area.name for dev_area in station_obj.dev_areas]
    dev_areas_dict = dict(list(zip(keys, station_obj.dev_areas)))
    for row in array:
        dev_area_obj = dev_areas_dict[row["NAME"]]
        dev_area_obj.__dict__[sum_attr] = row[sum_attr]


def _removeElement(obj_attribute, key):
    try:
        del obj_attribute[key]
    except KeyError:
        pass


# TOD TEMPLATES GEOPROCESSORS
# ----------------------------------------------------------------------------------------------
def createTODTemplatesGDB(in_folder, gdb_name, sr, use_defaults=True):
    # create tables/feature classes with proper schema
    tables = {
        "station_area_types": [
            ("stn_type", "TEXT", 50),
            ("res_target", "INTEGER"),
            ("job_target", "INTEGER"),
            ("hot_target", "INTEGER"),
            ("min_hot_sz", "INTEGER"),
            ("buff_area", "INTEGER"),
            ("dens_grad", "TEXT", 50),
            ("res_grad", "TEXT", 50),
        ],
        "technologies": [
            ("trans_tech", "TEXT", 50),
            ("res_target", "INTEGER"),
            ("job_target", "INTEGER"),
            ("hot_target", "INTEGER"),
            ("spd_target", "INTEGER"),
            ("spacing_sh", "INTEGER"),
            ("spacing_ln", "INTEGER"),
        ],
        "gradients": [
            ("gradient", "TEXT", 50),
            ("from_val", "INTEGER"),
            ("to_val", "INTEGER"),
            ("weight", "DOUBLE"),
        ],
    }
    points = {
        "stations": [
            ("stn_name", "TEXT", 50),
            ("stn_order", "INTEGER"),
            ("stn_type", "TEXT", 50),
        ]
    }
    arcpy.AddMessage("creating templates GDB")
    gdb = "{}\\{}".format(in_folder, gdb_name)
    if gdb[-4:] != ".gdb":
        gdb = gdb + ".gdb"
    if arcpy.Exists(gdb):
        arcpy.Delete_management(gdb)
    arcpy.CreateFileGDB_management(in_folder, gdb_name)

    for table_name in tables:
        arcpy.AddMessage("add table {}".format(table_name))
        arcpy.CreateTable_management(gdb, table_name)
        table_path = "{}\\{}".format(gdb, table_name)
        _addFieldsFromList(table_path, tables[table_name])
    for fc in points:
        arcpy.CreateFeatureclass_management(
            gdb, fc, geometry_type="POINT", spatial_reference=sr
        )
        fc_path = "{}\\{}".format(gdb, fc)
        _addFieldsFromList(fc_path, points[fc])

    if use_defaults:
        arcpy.AddMessage("populating default rows")
        station_area_type_fields = [
            field_spec[0] for field_spec in tables["station_area_types"]
        ]
        tech_fields = [field_spec[0] for field_spec in tables["technologies"]]
        gradient_fields = [field_spec[0] for field_spec in tables["gradients"]]
        _tables = ["station_area_types", "technologies", "gradients"]
        _defaults = [STATION_TYPE_DEFAULTS, TECH_DEFAULTS, GRADIENT_DEFAULTS]
        for table, default in zip(_tables, _defaults):
            arcpy.AddMessage("...{}".format(table))
            in_table = "{}\\{}".format(gdb, table)
            fields = [field_spec[0] for field_spec in tables[table]]
            if table == "gradients":
                _populateTableFromDict(
                    in_table, fields[0], fields[1:], default, multirow=True
                )
            else:
                _populateTableFromDict(in_table, fields[0], fields[1:], default)
    return gdb


def _generateTemplateReferences(in_gdb):
    stations_fc = "{}\\stations".format(in_gdb)
    tech_table = "{}\\technologies".format(in_gdb)
    station_type_table = "{}\\station_area_types".format(in_gdb)
    gradient_table = "{}\\gradients".format(in_gdb)
    technologies = createTechnologiesFromTable(
        tech_table,
        "trans_tech",
        "res_target",
        "job_target",
        "hot_target",
        "spd_target",
        "spacing_sh",
        "spacing_ln",
    )
    gradients = createGradientsFromTable(
        gradient_table, "gradient", "from_val", "to_val", "weight"
    )
    station_types = createStationTypesFromTable(
        station_type_table,
        "stn_type",
        "res_target",
        "job_target",
        "hot_target",
        density_gradient_field="dens_grad",
        res_mix_gradient_field="res_grad",
        gradients_dict=gradients,
        buffer_area_field="buff_area",
        min_hotel_size_field="min_hot_sz",
    )
    return stations_fc, technologies, station_types, gradients


def _addStationsToCorridor(
        corridor_obj, stations_fc, station_types_dict, technology_name, sr
):
    station_fields = ["stn_order", "stn_name", "stn_type", "SHAPE@"]
    with arcpy.da.SearchCursor(stations_fc, station_fields) as c:
        for r in c:
            order, station_name, station_type_name, point = r
            station_type_obj = station_types_dict[
                "{} - {}".format(station_type_name, technology_name)
            ]
            station_obj = Station(station_name, station_type_obj, order, point, sr)
            corridor_obj.insertStation(station_obj, order=order)


def _addDevAreasFromFishnet(
        stations_dict,
        fishnet_fc,
        fishnet_id,
        station_name_field,
        suitability_field=None,
        where_clause=None,
        sr=None,
        weight_by_area=False,
):
    if suitability_field:
        fields = [fishnet_id, station_name_field, suitability_field, "SHAPE@"]
    else:
        fields = [fishnet_id, station_name_field, "SHAPE@"]
    with arcpy.da.SearchCursor(
            fishnet_fc, fields, where_clause=where_clause, spatial_reference=sr
    ) as c:
        for r in c:
            dev_area_name = r[0]
            station_name = r[1]
            if suitability_field:
                suitability_score = r[2]
                if suitability_score is None:
                    suitability_score = 0.0
                dev_area_shape = r[3]
            else:
                suitability_score = None
                dev_area_shape = r[2]
            station_obj = stations_dict.get(station_name, None)
            if station_obj:
                if weight_by_area:
                    dev_area_area = dev_area_shape.area
                else:
                    dev_area_area = 1.0
                dev_area_obj = DevArea(
                    dev_area_name, dev_area_shape, sr, area=dev_area_area
                )
                dev_area_obj.setSuitability(suitability_score)
                station_obj.addDevArea(dev_area_obj)


def applyTODTemplates(
        in_gdb,
        fishnet_fc,
        fishnet_id,
        technology_name,
        fishnet_suitability_field=None,
        fishnet_where_clause="",
        sr=None,
        network_dataset=None,
        impedance_attribute=None,
        restrictions=None,
        preset_stations_field=None,
        weight_by_area=False,
        share_threshold=0.0,
):
    # generate supporting objects
    fishnet_id_dtype = HandyGP._getFieldDType(fishnet_fc, fishnet_id)
    arcpy.AddMessage("assembling TOD templates")
    stations_fc, technologies, station_types, gradients = _generateTemplateReferences(
        in_gdb
    )
    if not sr:
        sr = arcpy.Describe(stations_fc).spatialReference
    # set up corridor object
    arcpy.AddMessage("creating corridor")
    tech_obj = technologies[technology_name]
    corridor = Corridor(tech_obj, sr=sr)
    # add stations to corridor
    arcpy.AddMessage("compiling station locations")
    _addStationsToCorridor(corridor, stations_fc, station_types, technology_name, sr)

    # Create station area polygons
    #   set buffer field
    if preset_stations_field:
        target_field_name = preset_stations_field
    else:
        arcpy.AddMessage("defining station areas")
        buff_field = HandyGP._makeFieldName(stations_fc, "buffer")
        # TEMPORARY FIELD
        arcpy.AddField_management(stations_fc, buff_field, "INTEGER")
        try:
            with arcpy.da.UpdateCursor(stations_fc, ["stn_type", buff_field]) as c:
                for r in c:
                    station_type_name = r[0]
                    station_type = station_types[
                        "{} - {}".format(station_type_name, technology_name)
                    ]
                    r[1] = station_type.buffer_area
                    c.updateRow(r)
            # buffer stations
            arcpy.AddMessage("...buffering")
            station_areas_fc = "{}\\station_areas".format(in_gdb)
            if network_dataset:
                station_areas_fc = station_areas_fc + "_net"
                HandyGP.multiRingServiceAreaNoOverlap(
                    stations_fc,
                    "stn_name",
                    station_areas_fc,
                    network_dataset,
                    impedance_attribute,
                    restrictions,
                    sr=sr,
                    buffer_field=buff_field,
                )
            else:
                HandyGP.multiRingBufferNoOverlap(
                    stations_fc,
                    "stn_name",
                    station_areas_fc,
                    sr=sr,
                    buffer_field=buff_field,
                )
            # DELETE TEMPORARY FIELD
            arcpy.DeleteField_management(in_table=stations_fc, drop_field=buff_field)
        except:
            # DELETE TEMPORARY FIELD
            arcpy.DeleteField_management(in_table=stations_fc, drop_field=buff_field)
            raise
        # relate fishnet features to station area buffers
        arcpy.AddMessage("...assigning fishnet features to station areas")
        target_field_name = HandyGP._makeFieldName(fishnet_fc, "stn_name")
        arcpy.AddMessage("TARGET FIELD NAME: {}".format(target_field_name))
        HandyGP.maximumOverlapSpatialJoin(
            fishnet_fc,
            fishnet_id,
            station_areas_fc,
            "stn_name",
            "FIELD",
            in_expression=fishnet_where_clause,
            min_share=share_threshold,
        )
    expr = arcpy.AddFieldDelimiters(fishnet_fc, target_field_name) + " IS NOT NULL"
    if fishnet_where_clause:
        expr = " AND ".join([fishnet_where_clause, expr])
    # create development areas for each station
    arcpy.AddMessage("assembling station development areas")
    stations_dict = corridor._stationsToDict()
    _addDevAreasFromFishnet(
        stations_dict,
        fishnet_fc,
        fishnet_id,
        target_field_name,
        suitability_field=fishnet_suitability_field,
        where_clause=expr,
        sr=sr,
        weight_by_area=weight_by_area,
    )

    # apply targets and gradients for station areas
    arcpy.AddMessage("applying station area targets and gradients")
    if fishnet_suitability_field:
        use_suitability = True
    else:
        use_suitability = False
    for station in corridor.stations:
        arcpy.AddMessage("...{}".format(station.name))
        station.distributeTargetsToDevAreas(use_suitability=use_suitability)
    # apply adjustments to meet corridor targets if needed
    arcpy.AddMessage("applying corridor-level adjustments")
    # corridor.adjustStationActivitiesToTargets()

    # export tables of activities for corridor, station areas, dev areas
    arcpy.AddMessage("exporting output tables")
    _flag = ""
    if network_dataset:
        _flag = "_net"
    if fishnet_suitability_field:
        _flag = _flag + "_suit"
    corridor_sum_table = "{}\\corridor_activities{}".format(in_gdb, _flag)
    station_area_sum_table = "{}\\station_area_activities{}".format(in_gdb, _flag)
    dev_area_sum_table = "{}\\dev_area_activities{}".format(in_gdb, _flag)

    dev_area_dtype = np.dtype(
        [
            (str(fishnet_id), fishnet_id_dtype),
            ("DstToStn", "<f8"),
            ("TOTAL_ACT", "<f8"),
            ("RES", "<f8"),
            ("NONRES", "<f8"),
            ("JOB", "<f8"),
            ("HOTEL", "<f8"),
        ]
    )
    station_area_dtype = np.dtype(
        [("stn_name", "<U50"), ("RES", "<f8"), ("JOB", "<f8"), ("HOTEL", "<f8")]
    )
    corridor_dtype = np.dtype([("RES", "<f8"), ("JOB", "<f8"), ("HOTEL", "<f8")])

    dev_area_rows = [
        dev_area._convertToRow()
        for station in corridor.stations
        for dev_area in station.dev_areas
    ]
    station_area_rows = [station._convertToRow() for station in corridor.stations]
    corridor_rows = [corridor._convertToRow()]

    dev_area_array = np.array(dev_area_rows, dev_area_dtype)
    station_area_array = np.array(station_area_rows, station_area_dtype)
    corridor_array = np.array(corridor_rows, corridor_dtype)

    for table in [dev_area_sum_table, station_area_sum_table, corridor_sum_table]:
        if arcpy.Exists(table):
            arcpy.Delete_management(table)

    arcpy.da.NumPyArrayToTable(dev_area_array, dev_area_sum_table)
    arcpy.da.NumPyArrayToTable(station_area_array, station_area_sum_table)
    arcpy.da.NumPyArrayToTable(corridor_array, corridor_sum_table)


# TOD GEOPROCESSOR SUPPORT FUNCTIONS
# ----------------------------------------------------------------------------------------------
def createStationTypesFromTable(
        in_table,
        station_type_field,
        res_target_field,
        job_target_field,
        hotel_target_field,
        density_gradient_field=None,
        res_mix_gradient_field=None,
        gradients_dict=None,
        buffer_area_field=None,
        min_hotel_size_field=None,
        where_clause=None,
):
    fields = [
        station_type_field,
        res_target_field,
        job_target_field,
        hotel_target_field,
    ]
    if buffer_area_field:
        fields.append(buffer_area_field)
    if min_hotel_size_field:
        fields.append(min_hotel_size_field)
    if density_gradient_field:
        fields.append(density_gradient_field)
    if res_mix_gradient_field:
        fields.append(res_mix_gradient_field)
    station_types = {}
    with arcpy.da.SearchCursor(in_table, fields, where_clause=where_clause) as c:
        for r in c:
            station_type = r[0]
            res_target = r[1]
            job_target = r[2]
            hotel_target = r[3]
            i = 4
            buffer_area = None
            min_hotel_size = 50
            if buffer_area_field:
                buffer_area = r[i]
                i += 1
            if min_hotel_size_field:
                min_hotel_size = r[i]
                i += 1
            if density_gradient_field:
                density_gradient_name = r[i]
                density_gradient = gradients_dict[density_gradient_name]
                i += 1
            if res_mix_gradient_field:
                res_mix_gradient_name = r[i]
                res_mix_gradient = gradients_dict[res_mix_gradient_name]
                i += 1
            station_types[station_type] = StationType(
                station_type,
                res_target,
                job_target,
                hotel_target,
                min_hotel_size,
                buffer_area,
                density_gradient,
                res_mix_gradient,
            )
    return station_types


def createGradientsFromTable(
        in_table, gradient_field, from_field, to_field, weight_field, where_clause=None
):
    gradients = {}
    gradient_field_type = HandyGP._getFieldTypeName(in_table, gradient_field)
    quotes = ""
    if gradient_field_type == "TEXT":
        quotes = "'"
    fields = [from_field, to_field, weight_field]
    with arcpy.da.SearchCursor(
            in_table, gradient_field, where_clause=where_clause
    ) as c:
        gradient_names = sorted({r[0] for r in c})

    for gradient_name in gradient_names:
        gradient_obj = Gradient()
        expr = "".join(
            [
                arcpy.AddFieldDelimiters(in_table, gradient_field),
                "=",
                quotes,
                gradient_name,
                quotes,
            ]
        )
        with arcpy.da.SearchCursor(in_table, fields, where_clause=expr) as c:
            for r in c:
                from_val, to_val, weight = r
                gradient_obj.addValueRange(from_val, to_val, weight)
        gradients[gradient_name] = gradient_obj
    return gradients


def createTechnologiesFromTable(
        in_table,
        technology_field,
        res_target_field,
        job_target_field,
        hotel_target_field,
        speed_target_field,
        spacing_short_field,
        spacing_long_field,
        where_clause=None,
):
    fields = [
        technology_field,
        res_target_field,
        job_target_field,
        hotel_target_field,
        speed_target_field,
        spacing_short_field,
        spacing_long_field,
    ]
    technologies = {}
    with arcpy.da.SearchCursor(in_table, fields, where_clause=where_clause) as c:
        for r in c:
            tech, res_tgt, job_tgt, hotel_tgt, speed_tgt, spacing_s, spacing_l = r
            transit_tech_obj = TransitTech(
                tech, res_tgt, job_tgt, hotel_tgt, speed_tgt, spacing_s, spacing_l
            )
            technologies[tech] = transit_tech_obj
    return technologies


def _addFieldsFromList(in_table, fields):
    arcpy.AddMessage("fields:")
    for field in fields:
        arcpy.AddMessage("...{}".format(field))
        field_name = field[0]
        field_type = field[1]
        if field_type == "TEXT":
            field_length = field[2]
            arcpy.AddField_management(
                in_table, field_name, field_type, field_length=field_length
            )
        else:
            arcpy.AddField_management(in_table, field_name, field_type)


def _populateTableFromDict(in_table, name_field, fields, in_dict, multirow=False):
    _fields = [name_field] + fields
    with arcpy.da.InsertCursor(in_table, _fields) as c:
        for row_key in in_dict:
            field_dict = in_dict[row_key]
            if multirow:
                # if multirow:
                # {field: [v1, v2, ... vn]}
                rows = [field_dict[field] for field in fields if field != name_field]
                rows = list(map(list, list(zip(*rows))))
                for row in rows:
                    row.insert(0, row_key)
                    c.insertRow(row)
            else:
                row = [row_key]
                row += [field_dict[field] for field in fields if field != name_field]
                c.insertRow(row)


# SCENARIO GEOPROCESSORS
# ----------------------------------------------------------------------------------------------
def MultipatchToFootprint(
        multipatch_fc,
        footprints_fc,
        group_field=None,
        expression=None,
        estimate_volume=False,
        sr=None,
        volume_to_cumulative_area_factor=None,
):
    """
    Convert a multipach feature class to footprints.
    If estimate volume is True, compute area of footprint in
    spatial reference system specified (sr), estimate height
    based on z_max - z_min, and estimate volume as area * height
    """
    if not sr:
        sr = arcpy.Describe(multipatch_fc).spatialReference
    # convert multipatch features
    arcpy.AddMessage("converting Multipatch to Footprint")
    if expression:
        multipatch_fc = arcpy.MakeFeatureLayer_management(
            multipatch_fc, str(uuid.uuid1()), where_clause=expression
        )
    arcpy.MultiPatchFootprint_3d(multipatch_fc, footprints_fc, group_field)

    # calcualte footprint area in sr units
    arcpy.AddMessage("calculating footprint areas")
    arcpy.AddField_managment(footprints_fc, "calc_area", "DOUBLE")
    with arcpy.da.UpdateCursor(
            footprints_fc, ["SHAPE@", "calc_area"], spatial_reference=sr
    ) as c:
        for r in c:
            poly = r[0]
            area = poly.area
            r[1] = area
            c.updateRow(r)

    # estimate volume
    if estimate_volume:
        arcpy.AddMessage("estimating volumes")
        arcpy.AddField_management(footprints_fc, "est_height", "DOUBLE")
        arcpy.AddField_management(footprints_fc, "est_volume", "DOUBLE")
        arcpy.CalculateField_management(
            footprints_fc, "est_height", "!Z_Max! - !Z_Min!", "PYTHON"
        )
        arcpy.CalcualteField_management(
            footrpints_fc, "est_volume", "!est_height! * !calc_area!", "PYTHON"
        )
        if volume_to_cumulative_area_factor:
            arcpy.AddField_management(footprints_fc, "est_tot_area", "DOUBLE")
            arcpy.CalculateField_management(
                footprints_fc,
                "est_tot_area",
                "!est_volume!/int({})".format(volume_to_cumulative_area_factor),
                "PYTHON",
            )
    return footprints_fc


# summarizeFloorAreaInFishnet
def summarizeFloorAreaInFishnet(
        fishnet_features,
        fishnet_id_field,
        building_features,
        output_features,
        building_case_fields=[],
        building_where_clause=None,
        sr=None,
        building_floor_area_field=None,
        bldg_vol_to_fl_area_factor=12.0,
):
    convert_3d_To_2d = False
    desc = arcpy.Describe(building_features)
    if desc.shapeType == "MultiPatch":
        convert_3d_To_2d = True

    # setup outputs
    ##### check if this exists ?????
    if convert_3d_To_2d:
        building_features = "in_memory\\SFAIF_footprint"
        # convert building multipatch features to polygon footprints
        MultipatchToFootprint(
            building_features,
            footprints_fc,
            expression=building_where_clause,
            estimate_volume=True,
            sr=sr,
            volume_to_cumulative_area_factor=bldg_vol_to_fl_area_factor,
        )
    building_layer = HandyGP._cleanUUID(uuid.uuid1())
    arcpy.MakeFeatureLayer_management(
        building_features, building_layer, building_where_clause
    )

    # intersect fishnet with footprints
    intersect_fc = "in_memory\\SFAIF_int"
    arcpy.Intersect_analysis([fishnet_features, building_layer], intersect_fc)

    #####calculate areas by case ????
    # what is the area field called?
    # shore up units of area result?

    # Summarize
    stats_table = "in_memory\\SFAIF_stats"
    sum_field = ""  # ?????
    case_fields = [fisnet_id_field] + building_case_fields
    arcpy.Statistics_analysis(
        intersect_fc, stats_table, [["SUM", sum_field]], case_fields
    )


# post process results to account for existing/committed activity
def adjustTargetsBasedOnExisting(
        dev_areas_table,
        id_field,
        station_area_field,
        existing_hh_field,
        target_hh_field,
        existing_job_field,
        target_job_field,
        existing_hotel_field,
        target_hotel_field,
        out_table,
        where_clause=None,
):
    # dump dev_areas_table to dataframe
    fields = [
        id_field,
        station_area_field,
        existing_hh_field,
        existing_job_field,
        existing_hotel_field,
        target_hh_field,
        target_job_field,
        target_hotel_field,
    ]
    unique_fields = list(set(fields))
    dev_areas_df = pd.DataFrame(
        arcpy.da.TableToNumPyArray(
            dev_areas_table, unique_fields, where_clause=where_clause, null_value=0
        )
    )

    # get unique station areas
    station_areas = np.unique(dev_areas_df[station_area_field])
    result_dfs = []
    for station_area in station_areas:
        print(station_area)
        station_dev_areas = dev_areas_df[
            dev_areas_df[station_area_field] == station_area
            ].copy()
        # existng_hh_total = sum(station_dev_areas[existing_hh_field])
        # target_hh_total = sum(station_dev_areas[existing_hh_field])
        print("housing")
        station_dev_areas = _adjustTargets(
            station_dev_areas,
            id_field,
            target_hh_field,
            existing_hh_field,
            "HH_Target_PP",
        )
        print("jobs")
        station_dev_areas = _adjustTargets(
            station_dev_areas,
            id_field,
            target_job_field,
            existing_job_field,
            "Jobs_Target_PP",
        )
        print("hotels")
        station_dev_areas = _adjustTargets(
            station_dev_areas,
            id_field,
            target_hotel_field,
            existing_hotel_field,
            "Hotel_Target_PP",
        )
        result_dfs.append(station_dev_areas)

    dt_list = [
        (str(id_field), "<i4"),
        ("HH_Target_PP", "<f8"),
        ("Jobs_Target_PP", "<f8"),
        ("Hotel_Target_PP", "<f8"),
    ]
    df_stack = pd.concat(result_dfs)
    df_out = df_stack[[id_field, "HH_Target_PP", "Jobs_Target_PP", "Hotel_Target_PP"]]
    array_out = np.array(df_out.to_records(index=False), dtype=np.dtype(dt_list))
    arcpy.da.NumPyArrayToTable(array_out, out_table)


# post process results to account for existing/committed activity
def adjustTargetsBasedOnExisting2(
        dev_areas_table, 
        id_field, 
        station_area_field, 
        existing_fields, 
        target_fields, 
        out_fields, 
        out_table, 
        where_clause=None
        ):
    # dump dev_areas_table to dataframe
    fields = [id_field, station_area_field] + existing_fields + target_fields
    unique_fields = list(set(fields))
    print("Adjusting target values for fields:", target_fields)
    dev_areas_df = pd.DataFrame(
        arcpy.da.TableToNumPyArray(
            dev_areas_table, unique_fields, where_clause=where_clause, null_value=0
        )
    )

    # get unique station areas
    station_areas = np.unique(dev_areas_df[station_area_field])
    result_dfs = []
    for station_area in station_areas:
        print('...{}'.format(station_area))
        station_dev_areas = dev_areas_df[
            dev_areas_df[station_area_field] == station_area
            ].copy()
        # Update field values
        for ex_field, tgt_field, out_field in zip(
            existing_fields, target_fields, out_fields):
            station_dev_areas = _adjustTargets(
                station_dev_areas, id_field, tgt_field, ex_field, out_field
            )
        result_dfs.append(station_dev_areas)

    dt_list = [(str(id_field), "|S50")]
    dt_list.extend([(out_field, "<f8") for out_field in out_fields])
    df_stack = pd.concat(result_dfs)
    df_out_fields = [id_field] + out_fields
    df_out = df_stack[df_out_fields]
    array_out = np.array(df_out.to_records(index=False), dtype=np.dtype(dt_list))
    arcpy.da.NumPyArrayToTable(array_out, out_table)

def _adjustTargets(df, id_field, target_field, existing_field, result_field, depth=0):
    if sum(df[target_field]) == 0:
        df[result_field] = df[target_field]
        return df
    if depth > 50:
        df[result_field] = df[target_field]
        print("max iterations")
        return df
    # copy the df
    df_copy = df[[id_field, existing_field, target_field]].copy()

    # which cells have existing values higher than the targets?
    egtt_field = "__exist_gt_targ__"
    df_copy[egtt_field] = df_copy[existing_field] > df_copy[target_field]
    if len(df_copy[df_copy[egtt_field]]) > 0:
        # how much will the target increase at cells where EXIST_GT_TARG is True?
        df_copy["__new_target__"] = df_copy.apply(
            lambda row: _setNewTargetToExisting(
                row, existing_field, target_field, egtt_field
            ),
            axis=1,
        )

        # What is the total adjustment increment?
        total_adjustment_increment = sum(df_copy["__new_target__"])

        # How much higher is the target than the existing at cells where EXIST_GT_TARG is False?
        df_copy["__gap__"] = df_copy.apply(
            lambda row: _calcTargetGapAtGrowthCells(
                row, existing_field, target_field, egtt_field
            ),
            axis=1,
        )

        # what's the total of the new column __gap__?
        gap_total = sum(df_copy["__gap__"])

        if gap_total > 0:
            # What is each cell's share of __gap__?
            df_copy["__gap_share__"] = df_copy["__gap__"] / float(gap_total)

            # What is the amount by which each cell with a positive gap share needs to decrease?
            df_copy["__adjustment__"] = (
                    df_copy["__gap_share__"] * total_adjustment_increment
            )

            # What is the new target at adjusted cells?
            df_copy["__new_target__"] = df_copy.apply(
                lambda row: _reduceTargets(
                    row, target_field, "__adjustment__", existing_field, egtt_field
                ),
                axis=1,
            )
        else:
            df_copy["__new_target__"] = df_copy[existing_field]
        # Join result back to original df and re-submit
        df_merge = df.merge(
            df_copy[[id_field, "__new_target__"]], how="left", on=id_field
        )
        df_merge[target_field] = df_merge["__new_target__"]
        df_merge.drop(["__new_target__"], axis=1, inplace=True)
        return _adjustTargets(
            df_merge,
            id_field,
            existing_field,
            target_field,
            result_field,
            depth=depth + 1,
        )
    else:
        df_copy[result_field] = df_copy[target_field]
        df_merge = df.merge(df_copy[[id_field, result_field]], how="left", on=id_field)
        try:
            df_merge.drop(["__new_target__"], axis=1, inplace=True)
        except ValueError:
            pass
        return df_merge


def _setNewTargetToExisting(row, existing_col, target_col, flag_col):
    if row[flag_col]:
        return row[existing_col] - row[target_col]
    else:
        return 0.0


def _calcTargetGapAtGrowthCells(row, existing_col, target_col, flag_col):
    if row[flag_col]:
        return 0.0
    else:
        return row[target_col] - row[existing_col]


def _reduceTargets(row, target_col, adjustment_col, existing_col, condition_col):
    if row[condition_col]:
        return row[existing_col]
    elif row[target_col] - row[adjustment_col] < row[existing_col]:
        return row[existing_col]
    else:
        return row[target_col] - row[adjustment_col]


"""        
if __name__ == '__main__':      
    #### AD HOC TESTING ####
    in_gdb = r"K:\Projects\MiamiDade\Features\Kendall\Scenarios\temp\Test2.gdb"
    fishnet_fc = r"K:\Projects\MiamiDade\Features\Kendall\Scenarios\temp\Test2.gdb\fishnet"
    fishnet_id = "CELL_ID"
    technology_name = "LRT"
    sr = arcpy.SpatialReference(2881)
    fishnet_id_dtype = HandyGP._getFieldDType(fishnet_fc, fishnet_id)    
    stations_fc = "{}\\stations".format(in_gdb)
    tech_table = "{}\\technologies".format(in_gdb)  
    station_type_table = "{}\\station_area_types".format(in_gdb)
    gradient_table = "{}\\gradients".format(in_gdb)        

    technologies = createTechnologiesFromTable(tech_table, "trans_tech", "res_target",
                                    "job_target", "hot_target", "spd_target", "spacing_sh",
                                    "spacing_ln")
    gradients = createGradientsFromTable(gradient_table, "gradient", "from_val",
                                             "to_val", "weight")
    station_types = createStationTypesFromTable(station_type_table, "stn_type", "res_target",
                                    "job_target", "hot_target", density_gradient_field="dens_grad",
                                    res_mix_gradient_field="res_grad", gradients_dict=gradients,
                                    buffer_area_field="buff_area", min_hotel_size_field="min_hot_sz")       

    tech_obj = technologies[technology_name]
    corridor = Corridor(tech_obj, sr=sr)

    station_fields = ["stn_order", "stn_name", "stn_type", "SHAPE@"]
    with arcpy.da.SearchCursor(stations_fc, station_fields) as c:
        for r in c:
            order, station_name, station_type_name, point = r
            station_type_obj = station_types["{} - {}".format(station_type_name, technology_name)]
            station_obj = Station(station_name, station_type_obj, order, point, sr)
            corridor.insertStation(station_obj, order=order)

    station_areas_fc = "{}\\station_areas".format(in_gdb)
    target_field_name = "stn_name"
    expr = arcpy.AddFieldDelimiters(fishnet_fc, target_field_name) + " IS NOT NULL"

    stations_dict = corridor._stationsToDict()
    with arcpy.da.SearchCursor(fishnet_fc, [fishnet_id, target_field_name, "SHAPE@"],
                                   where_clause=expr, spatial_reference=sr) as c:
        i = 0
        for r in c:
            dev_area_name, station_name, dev_area_shape = r
            station_obj = stations_dict.get(station_name, None)
            if station_obj:
                dev_area_obj = DevArea(dev_area_name, dev_area_shape, sr)
                station_obj.addDevArea(dev_area_obj)
                i +=1
        print i

    for station in corridor.stations:
        station.distributeTargetsToDevAreas()
        print station.name, station.station_type.name, station.res_activity, station.job_activity, station.hotel_activity
        
    corridor.adjustStationActivitiesToTargets()
    for station in corridor.stations:
        print station.name, station.station_type.name, station.res_activity, station.job_activity, station.hotel_activity

    dev_area_rows = [dev_area._convertToRow() for station in corridor.stations for dev_area in station.dev_areas]
    station_area_rows = [station._convertToRow() for station in corridor.stations]
    corridor_rows = [corridor._convertToRow()]
               
    corridor_sum_table = "{}\\corridor_activities".format(in_gdb)
    station_area_sum_table = "{}\\station_area_activities".format(in_gdb)
    dev_area_sum_table = "{}\\dev_area_activities".format(in_gdb)

    corridor_dtype = np.dtype([("RES", "<f8"), ("JOB", "<f8"), ("HOTEL", "<f8")])    
    station_area_dtype = np.dtype([('stn_name', "<U50"), ("RES", "<f8"), ("JOB", "<f8"), ("HOTEL", "<f8")])
    dev_area_dtype = np.dtype([(fishnet_id, fishnet_id_dtype),("DstToStn", "<f8"),
                               ("TOTAL_ACT", "<f8"), ("RES", "<f8"), ("NONRES", "<f8"), ("JOB", "<f8"),
                               ("HOTEL", "<f8")])    
    
    corridor_array = np.array(corridor_rows, corridor_dtype)
    station_area_array = np.array(station_area_rows, station_area_dtype)
    dev_area_array = np.array(dev_area_rows, dev_area_dtype)

    for table in [corridor_sum_table, station_area_sum_table, dev_area_sum_table]:
        if arcpy.Exists(table):
            arcpy.Delete_management(table)

    arcpy.da.NumPyArrayToTable(corridor_array, corridor_sum_table)
    arcpy.da.NumPyArrayToTable(station_area_array, station_area_sum_table)
    arcpy.da.NumPyArrayToTable(dev_area_array, dev_area_sum_table)
    
"""
"""
#functions
def _addDevAreasFromFishnet2(stations_dict, fishnet_fc, fishnet_id, station_name_field, suitability_field,
                            where_clause=None, sr=None):
    fields = [fishnet_id, station_name_field, suitability_field, "SHAPE@"]
    with arcpy.da.SearchCursor(fishnet_fc, fields, where_clause=where_clause, spatial_reference=sr) as c:
        for r in c:
            dev_area_name, station_name, suitability_score, dev_area_shape = r
            station_obj = stations_dict.get(station_name, None)
            if station_obj:
                dev_area_obj = DevArea(dev_area_name, dev_area_shape, sr)
                dev_area_obj.setSuitability(suitability_score)
                station_obj.addDevArea(dev_area_obj)

#constants
fishnet_id = "CELL_ID"
suitability_field = "AvgSuit"

#input vars
in_gdb = r"K:\Projects\MiamiDade\Features\Kendall\Scenarios\Kendall_Data_Dec20_2017\MDC_Kendall_Scenario_2017_1211\TODEstimates\BRT_Draft4.gdb"
fishnet_fc = r"K:\Projects\MiamiDade\Features\Kendall\Scenarios\Kendall_Data_Dec20_2017\MDC_Kendall_Scenario_2017_1211\TODEstimates\BRT_Draft4.gdb\Fishnet_Draft4"
technology_name = "BRT"
target_field_name = "stn_name"


#workings
fishnet_id_dtype = HandyGP._getFieldDType(fishnet_fc, fishnet_id)
stations_fc, technologies, station_types, gradients = _generateTemplateReferences(in_gdb)
sr = arcpy.Describe(stations_fc).spatialReference
tech_obj = technologies[technology_name]
corridor = Corridor(tech_obj, sr=sr)
_addStationsToCorridor(corridor, stations_fc, station_types, technology_name, sr)
stations_dict = corridor._stationsToDict()
expr = arcpy.AddFieldDelimiters(fishnet_fc, target_field_name) + " IS NOT NULL"
"""

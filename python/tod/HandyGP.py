# HandyGP
# Author: Alex Bell, Renaissance Planning
# Date: November, 2017
# Description:
'''
This library provides convenient geoprocessing routines that build on arcpy
functionality, but augment those tools to simplify common tasks that require
multiple geoprocessors to be run.

Inventory:
   maximum overlap spatial join: spatially relate feature in the input feature class
       to features in the target feature class based on each input feature's
       cumulative overlap area with target features.  The input feature will be
       related to the single target feature with which it has the greatest amount
       of overlap.  Results can be stored in a new feature class or as a new field
       added to the input features.
    multi-ring buffer no overlap: create mutl-ring buffers around input features,
        ensuring that the buffers will not overlap.  The resulting polygons define
        the areas within each buffer threshold of each input feature where no other
        input feature is nearer.
    features to centroids: create points from polygons based on the polygon centroid
        location.  Optionally, group features and find the (weighted) centroid of the group.
    create fishnet: copy of arctoolbox Create Fishnet tool but honors selected features
        and where clauses.

'''

import arcpy
import numpy as np
import pandas as pd
import uuid
import copy

global _FIELD_TYPE_DICT, _FIELD_DTYPE_DICT

_FIELD_TYPE_DICT = {
    "String": "TEXT",
    "SmallInteger": "SHORT",
    "Integer": "LONG",
    "Single": "FLOAT",
    "Double": "DOUBLE",
    "Date": "DATE"
}
_FIELD_DTYPE_DICT = {
    "String": "U",
    "SmallInteger": "<i4",
    "Integer": "<i4",
    "Single": "<f8",
    "Double": "<f8",
    "Date": "M"  # ?
}


# geometry helpers
# --------------------------------------------------------------------------
class HandyAttribute(object):
    def __init__(self, name, field_type, value=None):
        self.name = name
        self.field_type = field_type
        self.value = value

    def setValue(self, value):
        if self.field_type in ["Integer", "SmallInteger"]:
            value = int(value)
        elif self.field_type in ['Single', 'Double', 'Float']:
            value = float(value)
        else:
            value = str(value)
        self.value = value


##    def makeFieldFromAttribute


##class HandyFC(object):
##    def __init__(geometry_type, sr=None):
##        self.geometry_type
##        self.sr = sr
##        self.fields = []
##
##    def addField

class HandyGeometry(object):
    def __init__(self, ID, shape, geometry_type=None, sr=None):
        self.ID = ID
        self.shape = shape
        self.geometry_type = geometry_type
        self.sr = sr
        self.attributes = {}

    def addAttribute(self, attr_obj):
        self.attributes[attr_obj.name] = attr_obj


##    def toFeatureClass(self, fc, overwrite=False):
##        #check if fc exists
##        if arcpy.Exists(fc):
##            if overwrite:
##                arcpy.Delete_management(fc)
##            else:
##                raise RuntimeError('feature class {} already exists'.format(fc))
##                return
##        path, name = fc.rsplit('\\',1)
##        arcpy.CreateFeatureclass_management(path, name, self.geometry_type,
##                                            spatial_reference=self.sr)
##        for attribute in self.attributes:


class HandyPoint(HandyGeometry):
    def __init__(self, ID, shape, sr=None):
        super(HandyPoint, self).__init__(ID, shape, geometry_type="POINT", sr=sr)


class HandyPolyline(HandyGeometry):
    def __int__(self, ID, shape, sr=None):
        super(HandyPolyline, self).__init__(ID, shape, geometry_type="POLYLINE", sr=sr)


class HandyPolygon(HandyGeometry):
    def __int__(self, ID, shape, sr=None):
        super(HandyPolyline, self).__init__(ID, shape, geometry_type="POLYGON", sr=sr)


# arcpy helpers
# --------------------------------------------------------------------------
def _getWorkspaceType(path):
    desc = arcpy.Describe(path)
    try:
        return desc.workspaceType
    except AttributeError:
        return _getWorkspaceType(desc.path)


def _makeFieldName(fc, new_field_name, seed=1):
    ws_type = _getWorkspaceType(fc)
    if ws_type == u'FileSystem':
        new_field_name = new_field_name[:10]
    if _checkNewFieldName(fc, new_field_name):
        if ws_type == u'FileSystem':
            new_field_name = new_field_name[:(10 - (len(str(seed)) + 1))] + "_" + str(seed)
        else:
            new_field_name = new_field_name + "_" + str(seed)
        return _makeFieldName(fc, new_field_name, seed + 1)
    else:
        return new_field_name


def _checkNewFieldName(fc, new_field_name):
    field_names = [f.name for f in arcpy.ListFields(fc)]
    return new_field_name in field_names


def _getFieldTypeName(fc, field_name):
    field = arcpy.ListFields(fc, field_name)[0]
    ftype = field.type
    return _FIELD_TYPE_DICT[ftype]


def _getDistanceBetweenPoints(point_1, point_2, sr):
    try:
        point_1 = arcpy.PointGeometry(point_1)
        point_2 = arcpy.PointGeometry(point_2)
    except RuntimeError:
        pass
    point_1 = point_1.projectAs(sr)
    return point_1.distanceTo(point_2.projectAs(sr))


def _createFishnetCoords(fc, where_clause=None, sr=None):
    if not sr:
        sr = arcpy.Describe(fc).spatialReference
    with arcpy.da.SearchCursor(fc, "SHAPE@", where_clause=where_clause,
                               spatial_reference=sr) as c:
        extents = [r[0].extent for r in c]
    x_min = min([extent.XMin for extent in extents])
    x_max = max([extent.XMax for extent in extents])
    y_min = min([extent.YMin for extent in extents])
    y_max = max([extent.YMax for extent in extents])
    origin = "{} {}".format(x_min, y_min)
    y_coord = "{} {}".format(x_min, y_min + 10)
    opposite_corner = "{} {}".format(x_max, y_max)
    return origin, y_coord, opposite_corner


def _cleanUUID(uuid_obj):
    return str(uuid_obj).replace('-', '_')


# numpy helpers
def _getFieldDType(fc, field_name):
    field = arcpy.ListFields(fc, field_name)[0]
    ftype = field.type
    dtype = _FIELD_DTYPE_DICT[ftype]
    if dtype == 'U':
        dtype = "{}{}".format(dtype, field.length)
    return dtype


# pandas helpers
def _makeArrayFromDf(df, dtype):
    try:
        array = np.array([tuple(row) for row in df.values], dtype)
    except ValueError:
        array = df.reset_index().values
        array = np.array([tuple(row) for row in array], dtype)
    return array


# Extend table with data frame
def extendTableDf(in_table, table_match_field, df, df_match_field, **kwargs):
    in_array = np.array(
        np.rec.fromrecords(
            df.values, names=df.dtypes.index.tolist()
        )
    )
    arcpy.da.ExtendTable(in_table=in_table,
                         table_match_field=table_match_field,
                         in_array=in_array,
                         array_match_field=df_match_field,
                         **kwargs)

def dfToArcpyTable(df, out_table):
    in_array = np.array(
        np.rec.fromrecords(
            df.values, names=df.dtypes.index.tolist()
        )
    )
    arcpy.da.NumPyArrayToTable(in_array, out_table)
# Maximum overlap spatial join
# ------------------------------------------------------------------------------------
def maximumOverlapSpatialJoin(in_features, in_id_field,
                              target_features, target_id_field,
                              output_type, output_fc=None,
                              in_expression="", target_expression="",
                              null_value=0, sr=None, min_share=0.0):
    '''output_type = ['FIELD', 'SHAPE'], in_id_field and target_id_field should be different'''

    # make feature layers
    in_layer = arcpy.MakeFeatureLayer_management(in_features, "xx__MOSJ_in__xx",  # str(uuid.uuid1())
                                                 where_clause=in_expression)
    target_layer = arcpy.MakeFeatureLayer_management(target_features, "xx__MOSJ_tar__xx",
                                                     where_clause=target_expression)
    # intersect feature layers, calculate overlapping areas
    arcpy.AddMessage("intersecting input features")
    intersect = "in_memory\\MOSJ_{}".format(_cleanUUID(uuid.uuid1()))
    # intersect = "in_memory\\MOSJ_int"
    arcpy.Intersect_analysis([in_layer, target_layer], intersect)
    oa_field = _makeFieldName(intersect, "OA")
    arcpy.AddField_management(intersect, oa_field, "DOUBLE")
    arcpy.AddMessage("calculating overlap areas")
    with arcpy.da.UpdateCursor(intersect, [oa_field, "SHAPE@"], spatial_reference=sr) as c:
        for r in c:
            poly = r[1]
            area = poly.area
            r[0] = area
            c.updateRow(r)

            # check fields in intersect table to get correct reference to target_id_field
    in_fields = arcpy.ListFields(in_features)
    in_fields = [f.name for f in in_fields if f.type != "Shape" and f.name not in ['Shape_Area', 'Shape_Length']]
    last_in_field = in_fields[-1]
    int_fields = arcpy.ListFields(intersect)
    int_fields = [f for f in int_fields if f.type != "Shape" and f.name not in ['Shape_Area', 'Shape_Length']]
    # print [f.aliasName for f in int_fields]
    last_in_field_idx = [f.name for f in int_fields].index(last_in_field)
    # print last_in_field_idx
    for target_field in int_fields[last_in_field_idx + 1:]:
        if target_field.aliasName == target_id_field:
            target_id_field_idx = int_fields.index(target_field)
            break
    #    elif target_field.name == target_id_field:
    #        target_id_field_idx = int_fields.index(target_field)
    #        break
    target_id_field_int = int_fields[target_id_field_idx].name

    # dissolve to get total overlap
    arcpy.AddMessage("dissolving overlap areas")
    dissolve = intersect + "Diss"
    arcpy.Dissolve_management(intersect, dissolve, [in_id_field, target_id_field_int],
                              "{} SUM".format(oa_field), "MULTI_PART")

    # record maximum overlap areas
    arcpy.AddMessage("finding maximum overlapping pairs")
    overlap_dict = {}
    with arcpy.da.SearchCursor(dissolve, [in_id_field, target_id_field_int, "SUM_{}".format(oa_field)]) as c:
        for r in c:
            i, t, oa = r
            cur_max = overlap_dict.get(i, (None, 0.0))
            if oa > cur_max[1]:
                cur_max = (t, oa)
            overlap_dict[i] = cur_max

    if output_type == 'FIELD':
        arcpy.AddMessage("updating attribute table")
        # create new fields for storing output
        # id field
        out_field_name = _makeFieldName(in_features, target_id_field)
        out_field_type = _getFieldTypeName(target_features, target_id_field)
        arcpy.AddField_management(in_features, out_field_name, out_field_type)
        # overlap area field
        oa_field = _makeFieldName(in_features, out_field_name + "_OA")
        arcpy.AddField_management(in_features, oa_field, "DOUBLE")
        # check workspace/null value
        ws_type = _getWorkspaceType(in_features)
        if ws_type != u'FileSystem':
            null_value = None
        # update attribute table
        with arcpy.da.UpdateCursor(in_features, [in_id_field, out_field_name, oa_field, "SHAPE@"]) as c:
            for r in c:
                i = r[0]
                t, oa = overlap_dict.get(i, (null_value, -1.0))
                tot_area = r[-1].area
                if oa / tot_area < min_share:
                    t, oa = (null_value, -1.0)
                r[1] = t
                r[2] = oa
                c.updateRow(r)
        return in_features
    else:
        # export intersect features to output_fc, including only those matching the max overlap area
        arcpy.AddMessage("Tagging and exporting maximum overlap features")
        keep_field = _makeFieldName(intersect, "KEEP")
        total_oa_field = _makeFieldName(intersect, "{}_OA".format(target_id_field))
        arcpy.AddField_management(intersect, keep_field, "SHORT")
        expr = arcpy.AddFieldDelimiters(intersect, keep_field) + "=1"
        # flag max overlap features
        with arcpy.da.UpdateCursor(intersect, [in_id_field, target_id_field,
                                               keep_field, total_oa_field]) as c:
            for r in c:
                i = r[0]
                t = r[1]
                T, oa = overlap_dict.get(i, (null_value, -1.0))
                if t == T:
                    r[2] = 1
                    r[3] = oa
                    c.updateRow(r)
        # export features where KEEP = 1
        out_ws, out_fc = output_fc.rsplit('\\', 1)
        arcpy.FeatureClassToFeatureClass_conversion(intersect, out_ws, out_fc,
                                                    where_clause=expr)
        return output_fc


# Multi-ring buffer, no overlap
# -----------------------------------------------------------------------------------
def multiRingBufferNoOverlap(in_features, id_field, output_fc,
                             sr=None, buffer_distances=[], buffer_field=None):
    if not sr:
        sr = arcpy.Describe(in_features).spatialReference

    # manage output_fc
    arcpy.AddMessage("creating output feature class")
    out_ws, out_name = output_fc.rsplit('\\', 1)
    if arcpy.Exists(output_fc):
        arcpy.Delete_management(output_fc)
    arcpy.CreateFeatureclass_management(out_ws, out_name, "POLYGON",
                                        spatial_reference=sr)
    id_field_type = _getFieldTypeName(in_features, id_field)
    arcpy.AddField_management(output_fc, id_field, id_field_type)
    arcpy.AddField_management(output_fc, "Buffer", "DOUBLE")

    # create buffer features
    arcpy.AddMessage("creating buffer features")
    fields = [id_field, "SHAPE@"]
    if buffer_field:
        fields.append(buffer_field)
    all_buffers = []
    with arcpy.da.SearchCursor(in_features, fields, spatial_reference=sr) as c:
        for r in c:
            in_id = r[0]
            in_point = r[1]
            if buffer_field:
                buffer_distances = [float(s) for s in str(r[2]).split(',')]
            h_pt = HandyPoint(in_id, in_point, sr=sr)
            for buffer_distance in buffer_distances:
                h_attr = HandyAttribute("Buffer", "Double", buffer_distance)
                h_poly = HandyPolygon(in_id, h_pt.shape.buffer(buffer_distance),
                                      sr=sr)
                h_poly.addAttribute(h_attr)
                x_attr = HandyAttribute("orig_x", "Double", h_poly.shape.centroid.X)
                y_attr = HandyAttribute("orig_y", "Double", h_poly.shape.centroid.Y)
                h_poly.addAttribute(x_attr)
                h_poly.addAttribute(y_attr)
                all_buffers.append(h_poly)

    # evaluate buffer overlaps and trim polygons
    revised_buffers = [copy.copy(buffer) for buffer in all_buffers]
    for this_buffer, rev_buffer in zip(all_buffers, revised_buffers):
        cutters = []
        for other_buffer in all_buffers:
            if this_buffer.ID != other_buffer.ID and not this_buffer.shape.disjoint(other_buffer.shape):
                # compare this buffer and the other buffer, cut if there is overlap
                intersect_points = this_buffer.shape.intersect(other_buffer.shape, 1)
                if intersect_points.partCount > 1:
                    ###
                    ####
                    from_pt = arcpy.PointGeometry(intersect_points.getPart(0)).projectAs(sr)
                    to_pt = arcpy.PointGeometry(intersect_points.getPart(1)).projectAs(sr)
                    angle_ft = from_pt.angleAndDistanceTo(to_pt, "PLANAR")[0]
                    angle_tf = to_pt.angleAndDistanceTo(from_pt, "PLANAR")[0]
                    new_to = to_pt.pointFromAngleAndDistance(angle_ft, 10, "PLANAR")
                    new_from = from_pt.pointFromAngleAndDistance(angle_tf, 10, "PLANAR")
                    cutter = arcpy.Polyline(arcpy.Array([new_from.centroid, new_to.centroid])).projectAs(sr)
                    cutters.append(cutter)
        # Cut up the polygon and keep the pieces nearest the original input point
        # _TEMP = r"K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scenarios\Fair_WE\TOD_buildout.gdb\cutters"
        # with arcpy.da.InsertCursor(_TEMP, ["SHAPE@", "ForStn"]) as c:
        #     for cutter in cutters:
        #         c.insertRow([cutter, this_buffer.ID])

        for cutter in cutters:
            this_shape = rev_buffer.shape
            if not this_shape.disjoint(cutter):
                cuts = this_shape.cut(cutter)
                this_orig_xy = arcpy.Point(
                    this_buffer.attributes["orig_x"].value, this_buffer.attributes["orig_y"].value)
                for cut in cuts:
                    if cut.contains(this_orig_xy):
                        rev_buffer.shape = cut

                    ####
                    ###
                    # cutter = arcpy.Polyline(intersect_points.getPart())

                    # measure distance from each cut to this buffer's centroid
                    # this_orig_xy = arcpy.Point(this_buffer.attributes["orig_x"].value, this_buffer.attributes["orig_y"].value)
                    # other_orig_xy = arcpy.Point(other_buffer.attributes["orig_x"].value, other_buffer.attributes["orig_y"].value)
                    # for cut in cuts:
                    #     this_dist = _getDistanceBetweenPoints(cut.centroid, this_orig_xy,
                    #                                           sr)
                    #     other_dist = _getDistanceBetweenPoints(cut.centroid, other_orig_xy,
                    #                                           sr)
                    #     if this_dist < other_dist:
                    #         this_buffer.shape = cut

    # record the buffer list as output features
    arcpy.AddMessage("...writing output features")
    with arcpy.da.InsertCursor(output_fc, [id_field, "Buffer", "SHAPE@"]) as c:
        for rev_buffer in revised_buffers:
            c.insertRow([rev_buffer.ID, rev_buffer.attributes['Buffer'].value,
                         rev_buffer.shape])
    return output_fc


def multiRingServiceAreaNoOverlap(in_features, id_field, output_fc, network_dataset,
                                  impedance_attribute, restrictions,
                                  sr=None, buffer_distances=[], buffer_field=None,
                                  detailed_polygons=False, trim_polygons_value='500 Feet'):
    ##    in_layer = arcpy.MakeFeatureLayer_management(in_features, "xx__MRSANO_in__xx", # str(uuid.uuid1())
    ##                                                 where_clause=in_expression)
    if not sr:
        sr = arcpy.Describe(in_features).spatialReference
    if detailed_polygons:
        polygon_type = "DETAILED_POLYS"
    else:
        polygon_type = "SIMPLE_POLYS"

    # manage output_fc
    arcpy.AddMessage("creating output feature class")
    out_ws, out_name = output_fc.rsplit('\\', 1)
    if arcpy.Exists(output_fc):
        arcpy.Delete_management(output_fc)

    # create and solve service area problem
    na_layer_name = "SA_{}".format(_cleanUUID(uuid.uuid1()))
    if not buffer_distances:
        buffer_distances = '1000'
    elif type(buffer) is list:
        buffer_distances = " ".join([str(bd) for bd in buffer_distances])
    arcpy.MakeServiceAreaLayer_na(network_dataset, na_layer_name, impedance_attribute,
                                  restriction_attribute_name=restrictions,
                                  default_break_values=buffer_distances, polygon_type=polygon_type,
                                  merge="NO_OVERLAP", nesting_type="DISKS", line_type="NO_LINES",
                                  polygon_trim="TRIM_POLYS", poly_trim_value=trim_polygons_value,
                                  hierarchy="NO_HIERARCHY", UTurn_policy="ALLOW_UTURNS")

    field_mappings = "Name {} #".format(id_field)
    if buffer_field:
        field_mappings = ";".join([field_mappings,
                                   "Breaks_{} {} #".format(impedance_attribute, buffer_field)])
    arcpy.AddLocations_na(na_layer_name, "Facilities", in_features, field_mappings, "5000 Meters",
                          match_type="MATCH_TO_CLOSEST", append="CLEAR",
                          exclude_restricted_elements="EXCLUDE")
    arcpy.Solve_na(na_layer_name, "SKIP", "TERMINATE")

    # add id field back to polygons outputs
    id_field_type = _getFieldTypeName(in_features, id_field)
    arcpy.AddFieldToAnalysisLayer_na(na_layer_name, "Polygons", id_field, id_field_type)

    # export outputs
    arcpy.CopyFeatures_management("{}\\Polygons".format(na_layer_name), "in_memory\\out_features")
    arcpy.Project_management("in_memory\\out_features", output_fc, sr)
    with arcpy.da.UpdateCursor(output_fc, ["Name", id_field]) as c:
        for r in c:
            _id = r[0].split(' : ')[0]
            r[1] = _id
            c.updateRow(r)

    return output_fc


# Features to centroids
# ------------------------------------------------------------------------------------
def FeaturesToCentroids(in_features, id_field, output_fc, where_clause=None,
                        weight_field=None, sr=None):
    # setup output_dtype:
    id_field_dtype = _getFieldDType(in_features, id_field)
    dt_list = [(id_field, id_field_dtype), ("SHAPE@X", '<f8'), ("SHAPE@Y", '<f8')]

    # dump in_features to array and convert to pd data frame
    arcpy.AddMessage("creating pandas data frame from input features")
    if not sr:
        sr = arcpy.Describe(in_polygons).spatialReference
    fields = [id_field] + groupd_fields + weight_fields + ["SHAPE@X", "SHAPE@Y"]
    array = arcpy.da.FeatureClassToNumPyArray(in_polygons, fields,
                                              where_clause=where_clause,
                                              spatial_reference=sr)
    df = pd.DataFrame(array)

    # summarize (weighted) cental points
    arcpy.AddMessage("finding centroid locations")
    if weight_field:
        arcpy.AddMessage("...weighted by {}".format(weight_field))
        weight_field_dtype = _getFieldDType(in_features, weight_field)
        dt_list.append((weight_field, weight_field_dtype))
        # create product sums
        for coord in ['X', 'Y']:
            df["SHAPE@{}_".format(coord)] = df["SHAPE@{}".format(coord)]
            df["SHAPE@{}".format(coord)] = df["SHAPE@{}_".format(coord)] * df[weight_field]
        df_sum = df.groupby([id_field])["SHAPE@X", "SHAPE@Y", weight_field].sum()
    else:
        df_sum = df.groupby([id_field])["SHAPE@X", "SHAPE@Y"].sum()
    out_array = _makeArrayFromDf(df_sum, np.dtype(dt_list))

    # export output
    arcpy.AddMessage("writing output features")
    arcpy.da.NumPyArrayToFeatureClass(out_array, output_fc, ["SHAPE@X", "SHAPE@Y"],
                                      spatial_reference=sr)
    return output_fc


# Create fishnet
# ------------------------------------------------------------------------------------
def createFishnet(in_features, output_fc, cell_width=None, cell_height=None,
                  number_of_rows=None, number_of_columns=None,
                  geometry_type="POLYGON", where_clause=None, sr=None,
                  create_label_points=False):
    if not sr:
        sr = arcpy.Describe(in_features).spatialReference
    if create_label_points:
        labels = "LABELS"
    else:
        labels = "NO_LABELS"
    arcpy.AddMessage('Finding extents')
    origin, y_coord, opposite_corner = _createFishnetCoords(in_features, where_clause=where_clause, sr=sr)
    arcpy.AddMessage('Creating fishnet featuers')
    arcpy.CreateFishnet_management(output_fc, origin, y_coord, cell_width, cell_height,
                                   number_of_rows, number_of_columns, opposite_corner,
                                   labels, geometry_type=geometry_type)
    arcpy.DefineProjection_management(output_fc, sr)
    # create a cell ID field
    arcpy.AddMessage('Updating cell id')
    arcpy.AddField_management(output_fc, "CELL_ID", "LONG")
    cell_id = 1
    with arcpy.da.UpdateCursor(output_fc, "CELL_ID") as c:
        for r in c:
            r[0] = cell_id
            c.updateRow(r)
            cell_id += 1
    return output_fc


if __name__ == "__main__":
    taz = r"K:\Projects\MAPC\Features\Model\CTPS_full_model_TAZ.shp"
    block = r"K:\Projects\MAPC\Features\Census\tl_2010_25_tabblock10\tl_2010_25_tabblock10.shp"
    sr_ref = r"K:\Projects\MAPC\Features\LU\MassDOT_Allston.gdb\Allston_CAD\Polyline"
    sr = arcpy.Describe(sr_ref).spatialReference

    maximumOverlapSpatialJoin(block, "GEOID10", taz, "ID", "FIELD", sr=sr)

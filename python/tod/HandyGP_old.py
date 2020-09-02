#HandyGP
#Author: Alex Bell, Renaissance Planning
#Date: November, 2017
#Description:
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

global _FIELD_TYPE_DICT, _FIELD_DTYPE_DICT

_FIELD_TYPE_DICT = {
    "String":"TEXT",
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
    "Date": "M" #?
    }


#geometry helpers
#--------------------------------------------------------------------------
class HandyAttribute(object):
    def __init__(self, name, field_type):
        self.name = name
        self.field_type = field_type        
        self.value = None

    def setValue(self, value):
        if self.field_type in ["Integer", "SmallInteger"]:
            value = int(value)
        elif self.field_type in ['Single', 'Double', 'Float']:
            value = float(value)
        else:
            value = str(value)
        self.value = value
                

class HandyGeometry(object):
    def __init__(self, ID, shape, sr=None):
        self.ID = ID
        self.shape = shape
        self.sr = sr
        self.attributes = {}
        
    def addAttribute(self, attr_obj):
        self.attributes[attr_obj.name] = attr_obj
        

class HandyPoint(HandyGeometry):
    def __init__(self, ID, shape, sr=None):
        super(HandyPoint, self).__init__(ID, shape, sr=sr)
        

class HandyPolyline(HandyGeometry):
    def __int__(self, ID, shape, sr=None):
        super(HandyPolyline, self).__init__(ID, shape, sr=sr)


class HandyPolygon(HandyGeometry):
    def __int__(self, ID, shape):
        super(HandyPolyline, self).__init__(ID, shape)


#arcpy helpers
#--------------------------------------------------------------------------
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
            new_field_name = new_fiele_name + "_" + str(seed)
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
    return str(uuid_obj).replace('-','_')


#numpy helpers
def _getFieldDType(fc, field_name):
    field = arcpy.ListFields(fc, field_name)[0]
    ftype = field.type
    dtype = _FIELD_DTYPE_DICT[ftype]
    if dtype == 'U':
        dtype = "{}{}".format(dtype, field.length)
    return dtype


#pandas helpers
def _makeArrayFromDf(df, dtype):
    try:
        array = np.array([tuple(row) for row in df.values], dtype)
    except ValueError:
        array = df.reset_index().values
        array = np.array([tuple(row) for row in array], dtype)
    return array


#Maximum overlap spatial join
#------------------------------------------------------------------------------------ 
def maximumOverlapSpatialJoin(in_features, in_id_field,
                              target_features, target_id_field,
                              output_type, output_fc=None,
                              in_expression="", target_expression="",
                              null_value=0):
    '''output_type = ['FIELD', 'SHAPE'], in_id_field and taret_id_field should be different'''

    #make feature layers
    in_layer = arcpy.MakeFeatureLayer_management(in_features, str(uuid.uuid1()),
                                                 where_clause=in_expression)
    target_layer = arcpy.MakeFeatureLayer_management(target_features, str(uuid.uuid1()),
                                                     where_clause=target_expression)
    #intersect feature layers, calculate overlapping areas
    arcpy.AddMessage("intersecting input features")
    intersect = arcpy.Intersect_analysis(in_layer, "in_memory\\MOSJ_{}".format(_cleanUUID(uuid.uuid1())))
    oa_field = _makeFieldName(intersect, "OA")
    arcpy.AddField_management(intersect, oa_field, "DOUBLE")
    arcpy.AddMessage("calculating overlap areas")
    arcpy.CalculateField_management(intersect, oa_field, '!shape.area@squarefeet!', "PYTHON")

    #dissolve to get total overlap
    arcpy.AddMessage("dissolving overlap areas")
    dissolve = arcpy.Dissolve_management(intersect, 'in_memory\\MOSJdis_{}'.format(_cleanUUID(uuid.uuid1())),
                                         [in_id_field, target_id_field], "{} SUM".format(oa_field),
                                         "MULTI_PART")

    #record maximum overlap areas
    arcpy.AddMessage("finding maximum overlapping pairs")
    overlap_dict = {}
    with arcpy.da.SearchCursor(dissolve, [in_id_field, target_id_field, "{} SUM".format(oa_field)]) as c:
        for r in c:
            i, t, oa = r
            cur_max = overlap_dict.get(i,(None, 0.0))
            if oa > cur_max[1]:
                cur_max = (t, oa)
            overlap_dict[i] = cur_max

    if output_type == 'FIELD':
        arcpy.AddMessage("updating attribute table")
        #create new fields for storing output      
        out_field_name = _makeFieldName(in_features, target_id_field)
        out_field_type = _getFieldTypeName(target_features, target_id_field)
        oa_field = _makeFieldName(in_features, out_field_name + "_OA")
        arcpy.AddField_management(in_features, out_field_name, out_field_type)
        arcpy.AddField_management(in_features, oa_field, "DOUBLE")
        #check workspace/null value
        ws_type = _getWorkspaceType(in_features)
        if ws_type != u'FileSystem':
            null_value=None
        #update attribute table
        with arcpy.da.UpdateCursor(in_features, [in_id_field, out_field_name, oa_field]) as c:
            for r in c:
                i = r[0]
                t, oa = overlap_dict.get(i, (null_value, -1.0))
                r[1] = t
                r[2] = oa
                c.updateRow(r)
        return in_features
    else:
        #export intersect features to output_fc, including only those matching the max overlap area
        arcpy.AddMessage("Tagging and exporting maximum overlap features")
        keep_field = _makeFieldName(intersect, "KEEP")
        total_oa_field = _makeFieldName(intersect, "{}_OA".format(target_id_field))
        arcpy.AddField_management(intersect, keep_field, "SHORT")
        expr = arcpy.AddFieldDelimiters(intersect, keep_field) + "=1"
        #flag max overlap features
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
        #export features where KEEP = 1
        out_ws, out_fc = output_fc.rsplit('\\',1)
        arcpy.FeatureClassToFeatureClass_conversion(intersect, out_ws, out_fc,
                                                    where_clause=expr)
        return output_fc


#Multi-ring buffer, no overlap
#-----------------------------------------------------------------------------------     
def multiRingBufferNoOverlap(in_features, id_field, output_fc,
                             sr=None, buffer_distances=[], buffer_field=None):
    ###
    ### !!!!! field-based buffer!!!!!
    ###
    ###
    if not sr:
        sr = arcpy.Describe(in_features).spatialReference
    #manage output_fc
    arcpy.AddMessage("creating output feature class")
    out_ws, out_name = output_fc.rsplit('\\', 1)
    if arcpy.Exists(output_fc):
        arcpy.Delete_management(output_fc)

    arcpy.CreateFeatureclass_management(out_ws, out_name, "POLYGON",
                                        spatial_reference=sr)
    id_field_type = _getFieldTypeName(in_features, id_field)
    arcpy.AddField_management(output_fc, id_field, id_field_type)
    arcpy.AddField_management(output_fc, "Buffer", "DOUBLE")

    #create buffer features, accounting for overlaps with neighbors    
    arcpy.AddMessage("creating buffer features")
    fields = [id_field, "SHAPE@"]
    if buffer_field:
        fields.append(buffer_field)
    with arcpy.da.SearchCursor(in_features, fields, spatial_reference=sr) as c:
        for r in c:
            in_id = r[0]
            in_pt = r[1]
            if buffer_field:
                buffer_distances = r[2].split(',')
            h_pt = HandyPoint(in_id, in_point, sr=sr)
                        



    
    buffer_distances.sort()
    for buffer_distance in buffer_distances:
        arcpy.AddMessage("...{}".format(buffer_distance))
        #make ad hoc buffer features
        buffers = []
        id_list = []        
        with arcpy.da.SearchCursor(in_features, [id_field, "SHAPE@"],
                                   spatial_reference=sr) as c:
            for r in c:
                in_id, in_point = r
                in_buffer = in_point.buffer(buffer_distance)
                buffers.append(in_buffer)
                id_list.append(in_id)
        #modify buffer features if needed
        arcpy.AddMessage("...analyzing overlap areas")
        buffer_idx = 0
        for this_id, this_buffer in zip(id_list, buffers):
            for other_id, other_buffer in zip(id_list, buffers):
                if not this_buffer.disjoint(other_buffer) and this_id != other_id:
                    #this buffer intersects the other buffer
                    #cut this buffer
                    intersect_points = this_buffer.intersect(other_buffer, 1)
                    if intersect_points.partCount > 1:
                        cutter = arcpy.Polyline(intersect_points.getPart())
                        cuts = this_buffer.cut(cutter.projectAs(sr))
                        #measure distance from each cut to this input feature (buffer centroid)
                        for cut in cuts:
                            this_dist = _getDistanceBetweenPoints(cut.centroid, this_buffer.centroid, sr)
                            other_dist = _getDistanceBetweenPoints(cut.centroid, other_buffer.centroid, sr)
                            #the nearer feature is retained and the buffer list updated
                            if this_dist < other_dist:
                                this_buffer = cut
                                buffers[buffer_idx] = this_buffer
            buffer_idx += 1

        #record the buffer list as output features
        arcpy.AddMessage("...writing output features")
        with arcpy.da.InsertCursor(output_fc, [id_field, "Buffer", "SHAPE@"]) as c:
            for this_id, this_buffer in zip(id_list, buffers):
                c.insertRow([this_id, buffer_distance, this_buffer])
    return output_fc
            

#Features to centroids
#------------------------------------------------------------------------------------
def FeaturesToCentroids(in_features, id_field, output_fc, where_clause=None,
                       weight_field=None, sr=None):
    #setup output_dtype:
    id_field_dtype = _getFieldDType(in_features, id_field)
    dt_list = [(id_field, id_field_dtype), ("SHAPE@X", '<f8'), ("SHAPE@Y", '<f8')]
    
    #dump in_features to array and convert to pd data frame
    arcpy.AddMessage("creating pandas data frame from input features")
    if not sr:
        sr = arcpy.Describe(in_polygons).spatialReference
    fields = [id_field] + groupd_fields + weight_fields + ["SHAPE@X", "SHAPE@Y"]
    array = arcpy.da.FeatureClassToNumPyArray(in_polygons, fields,
                                              where_clause=where_clause,
                                              spatial_reference=sr)
    df = pd.DataFrame(array)
    
    #summarize (weighted) cental points
    arcpy.AddMessage("finding centroid locations")
    if weight_field:
        arcpy.AddMessage("...weighted by {}".format(weight_field))
        weight_field_dtype = _getFieldDType(in_features, weight_field)
        dt_list.append((weight_field, weight_field_dtype))
        #create product sums
        for coord in ['X', 'Y']:
            df["SHAPE@{}_".format(coord)] = df["SHAPE@{}".format(coord)]
            df["SHAPE@{}".format(coord)] = df["SHAPE@{}_".format(coord)]* df[weight_field]
        df_sum = df.groupby([id_field])["SHAPE@X", "SHAPE@Y", weight_field].sum()
    else:
         df_sum = df.groupby([id_field])["SHAPE@X", "SHAPE@Y"].sum()
    out_array = _makeArrayFromDf(df_sum, np.dtype(dt_list))

    #export output
    arcpy.AddMessage("writing output features")
    arcpy.da.NumPyArrayToFeatureClass(out_array, output_fc, ["SHAPE@X", "SHAPE@Y"],
                                      spatial_reference=sr)
    return output_fc
    

#Create fishnet
#------------------------------------------------------------------------------------
def createFishnet(in_features, output_fc, cell_width=None, cell_height=None,
                  number_of_rows=None, number_of_columns=None,
                  geometry_type="POLYGON", where_clause=None, sr=None,
                  create_label_points=False):
    if not sr:
        sr = arcpy.Describe(in_features).spatialReference
    if create_label_points:
        labels="LABELS"
    else:
        labels="NO_LABELS"
    arcpy.AddMessage('Finding extents')
    origin, y_coord, opposite_corner = _createFishnetCoords(in_features, where_clause=where_clause, sr=sr)
    arcpy.AddMessage('Creating fishnet featuers')
    arcpy.CreateFishnet_management(output_fc, origin, y_coord, cell_width, cell_height,
                                   number_of_rows, number_of_columns, opposite_corner,
                                   labels, geometry_type=geometry_type)
    #create a cell ID field
    arcpy.AddMessage('Updating cell id')
    arcpy.AddField_management(output_fc, "CELL_ID", "LONG")
    cell_id = 1
    with arcpy.da.UpdateCursor(output_fc, "CELL_ID") as c:
        for r in c:
            r[0] = cell_id
            c.updateRow(r)
            cell_id += 1
    return output_fc
        






                                   

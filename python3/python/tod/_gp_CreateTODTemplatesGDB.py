#Create TOD Templates GDB
import arcpy
from . import TOD

if __name__ == '__main__':
    in_folder = arcpy.GetParameterAsText(0) # workspace, local database
    gdb_name = arcpy.GetParameterAsText(1) #string
    sr = arcpy.GetParameter(2) # spatial reference
    use_defaults = arcpy.GetParameter(3) # boolean

    TOD.createTODTemplatesGDB(in_folder, gdb_name, sr,
                              use_defaults=use_defaults)

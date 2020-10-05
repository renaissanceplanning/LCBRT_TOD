import arcpy
import os, sys
from arcgis.gis import GIS

### Start setting variables
# Set the path to the project
scripts_folder = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
prjPath = os.path.join(scripts_folder, 'maps', 'LCBRT_maps', 'LCBRT_maps.aprx')

# Update the following variables to match:
# Feature service/SD name in arcgis.com, user/password of the owner account
sd_fs_name = "WE_Sum"
portal = "http://www.arcgis.com" # Can also reference a local portal
user = "crudder_renplan"
password = "1%8CGBrI53Gg"

# Set sharing options
shrOrg = False
shrEveryone = False
shrGroups = ""

### End setting variables

# Local paths to create temporary content
relPath = os.path.join(scripts_folder, 'maps')
sddraft = os.path.join(relPath, "WebUpdate.sddraft")
sd = os.path.join(relPath, "WebUpdate.sd")

# Create a new SDDraft and stage to SD
print("Creating SD file")
arcpy.env.overwriteOutput = True
prj = arcpy.mp.ArcGISProject(prjPath)
maps = prj.listMaps()
for m in maps:
    if m.name == "WE_Sum":
        # layers = m.listLayers():
        # for layer in layers:
        #     if layer.isBasemapLayer():
        #         arcpy.mp.
        arcpy.mp.CreateWebLayerSDDraft(
            map_or_layers=m, 
            out_sddraft=sddraft, 
            service_name=sd_fs_name, 
            server_type='HOSTING_SERVER', 
            service_type='FEATURE_ACCESS', 
            folder_name='', 
            overwrite_existing_service=True, 
            copy_data_to_server=True,
            enable_editing=True,)
        arcpy.StageService_server(
            in_service_definition_draft=sddraft, 
            out_service_definition=sd)

print("Connecting to {}".format(portal))
gis = GIS(portal, user, password)

# Find the SD, update it, publish /w overwrite and set sharing and metadata
print("Search for original SD on portal…")
sdItem = gis.content.search(query=f"title:{sd_fs_name} AND owner:{user}", item_type="Service Definition")[0]
print(f"Found SD: {sdItem.title}, ID: {sdItem.id} n Uploading and overwriting…")
sdItem.update(data=sd)
print("Overwriting existing feature service…")
fs = sdItem.publish(overwrite=True)

if shrOrg or shrEveryone or shrGroups:
  print("Setting sharing options…")
  fs.share(org=shrOrg, everyone=shrEveryone, groups=shrGroups)

print(f"Finished updating: {fs.title} – ID: {fs.id}")
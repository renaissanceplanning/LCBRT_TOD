import arcpy
import os, sys
from arcgis.gis import GIS
from pathlib import Path


def get_group_id(group_name, owner):
    gis = GIS(portal, user, password)
    try:
        group = gis.groups.search(query=f"title: {group_name} AND owner: {owner}")
        return group[0].id
    except:
        return None


''' Start setting variables '''
# Set the path to the project
# scripts_folder = Path(__file__).resolve().parent.parent
scripts_folder = r'K:\Projects\BCDCOG\Features\Files_For_RDB\RDB_V3\scripts'
project_path = Path(scripts_folder, 'maps', 'LCBRT_maps', 'LCBRT_maps.aprx')

# user/password of the owner account
portal = "http://www.arcgis.com"  # Can also reference a local portal
user = "crudder_renplan"
password = "1%8CGBrI53Gg"

# Set sharing options
shr_to_org = True
shr_to_everyone = False
shr_with_groups = get_group_id(group_name='Low Country BRT - TOD',
                               owner=user)  # GroupID unique identifier

# Feature service/SD name in arcgis.com,
service_names = ["WE_Sum", "WE_Fair"]

# local path
LOCAL_PATH = Path(scripts_folder, 'maps')
''' End setting variables '''


def update_fs_from_map(pro_project, map_name, service_name):
    # Local paths to create temporary content
    draft = Path(LOCAL_PATH, f"{service_name}_WebUpdate.sddraft")
    service_def = f"{service_name}_WebUpdate.sd"
    service_def_path = Path(LOCAL_PATH, service_def)

    #: Delete draft and definition if existing
    for file_path in (draft, service_def_path):
        if file_path.exists():  #: This check can be replaced in 3.8 with missing_ok=True
            print(f'deleting existing {file_path}...')
            file_path.unlink()

    # Create a new SDDraft and stage to SD
    print("Creating SD file")
    arcpy.env.overwriteOutput = True
    prj = arcpy.mp.ArcGISProject(pro_project)
    for m in prj.listMaps():
        if m.name == map_name:
            arcpy.mp.CreateWebLayerSDDraft(
                map_or_layers=m,
                out_sddraft=draft,
                service_name=service_name,
                server_type='HOSTING_SERVER',
                service_type='FEATURE_ACCESS',
                folder_name='',
                overwrite_existing_service=True,
                copy_data_to_server=True,
                enable_editing=True, )
            arcpy.StageService_server(
                in_service_definition_draft=draft,
                out_service_definition=service_def)

    print("Connecting to {}".format(portal))
    gis = GIS(portal, user, password)

    # check to see if the service exists and overwrite, otherwise publish new service
    try:
        print("Search for original SD on portal…")
        service_def_item = gis.content.search(query=f"title:{service_name} AND owner:{user}",
                                              item_type="Service Definition")[0]
        print(f"Found SD: {service_def_item.title}, ID: {service_def_item.id} n Uploading and overwriting…")
        service_def_item.update(data=str(service_def))
        print("Overwriting existing feature service…")
        feature_service = service_def_item.publish(overwrite=True)
    except:
        print("The service doesn't exist, creating new")
        print("...uploading new content")
        source_item = gis.content.add(item_properties={}, data=str(service_def))
        print("...publisihing new content")
        feature_service = source_item.publish()

    if shr_to_org or shr_to_everyone or shr_with_groups:
        print("Setting sharing options…")
        feature_service.share(org=shr_to_org, everyone=shr_to_everyone, groups=shr_with_groups)


if __name__ == "__main__":
    for service in service_names:
        update_fs_from_map(
            pro_project=project_path,
            map_name=service,
            service_name=service)
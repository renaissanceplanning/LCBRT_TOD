import arcpy
from os import path, remove
from arcgis.gis import GIS
from arcgis.mapping import WebMap
# from pathlib import Path


def get_group_id(group_name, owner):
    gis = GIS(portal, user, password)
    try:
        group = gis.groups.search(query=f"title: {group_name} AND owner: {owner}")
        return group[0].id
    except:
        return None


''' Start setting variables '''
# Set the path to the project
scripts_folder = r'C:\Users\V_RPG\OneDrive - Renaissance Planning Group\SHARE\LCBRT_DATA\scripts'
# scripts_folder = path.dirname(path.abspath(__file__))
project_path = r"C:\Users\V_RPG\Desktop\MDPMT_Testreplace\test_replace_project\test_replace_project.aprx"

# user/password of the owner account
portal = "http://www.arcgis.com"  # Can also reference a local portal
user = "crudder_renplan"
password = "1%8CGBrI53Gg"

# Set sharing options
shr_to_org = True
shr_to_everyone = False
shr_with_groups = get_group_id(group_name='test_crowdsource',
                               owner=user)  # GroupID unique identifier

# Feature service/SD name in arcgis.com,
service_names = ["WE_Sum", "WE_Fair"]

# local path
LOCAL_PATH = path.join(scripts_folder, 'maps')
''' End setting variables '''

def get_wm_item_id(gis, wm_title, item_type="Web Map"):
    try:
        wm_search = gis.content.search(f"title: {wm_title}", item_type=item_type)
        for wm in wm_search:
            if wm.title == wm_title:
                return wm.id
    except AttributeError:
        print("no web map by that name exists, cannot find id to publish")

def update_wm_from_map(pro_project, map_name, map_service):

def update_fs_from_map(pro_project, map_name, service_name):
    # Local paths to create temporary content
    draft_path = path.join(LOCAL_PATH, f"{service_name}_WebUpdate.sddraft")
    service_def_path = path.join(LOCAL_PATH, f"{service_name}_WebUpdate.sd")

    #: Delete draft and definition if existing
    for file_path in (draft_path, service_def_path):
        if path.exists(file_path):  #: This check can be replaced in 3.8 with missing_ok=True
            print(f'deleting existing {file_path}...')
            remove(file_path)

    # Create a new SDDraft and stage to SD
    print("Creating SD file")
    arcpy.env.overwriteOutput = True
    prj = arcpy.mp.ArcGISProject(pro_project)
    for m in prj.listMaps():
        if m.name == map_name:
            arcpy.mp.CreateWebLayerSDDraft(
                map_or_layers=m,
                out_sddraft=draft_path,
                service_name=service_name,
                server_type='HOSTING_SERVER',
                service_type='FEATURE_ACCESS',
                folder_name='',
                overwrite_existing_service=True,
                copy_data_to_server=True,
                enable_editing=True, )
            arcpy.StageService_server(
                in_service_definition_draft=draft_path,
                out_service_definition=service_def_path)

    print("Connecting to {}".format(portal))
    gis = GIS(portal, user, password)

    # check to see if the service exists and overwrite, otherwise publish new service
    try:
        print("Search for original SD on portal…")
        service_def_item = gis.content.search(query=f"title:{service_name} AND owner:{user}",
                                              item_type="Service Definition")[0]
        print(f"Found SD: {service_def_item.title}, \n\tID: {service_def_item.id} \n...Uploading and overwriting…")
        service_def_item.update(data=str(service_def_path))
        print("Overwriting existing feature service…")
        feature_service = service_def_item.publish(overwrite=True)
    except:
        print("The service doesn't exist, creating new")
        print("...uploading new content")
        source_item = gis.content.add(item_properties={}, data=str(service_def_path))
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
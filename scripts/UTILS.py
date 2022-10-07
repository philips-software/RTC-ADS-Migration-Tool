import os
import CONFIG
import RTC
import shutil
import requests
from datetime import datetime
from azure.devops.v5_0.work_item_tracking.models import JsonPatchOperation
from azure.devops.v5_1.work_item_tracking.models import Comment
from azure.devops.v5_1.work_item_tracking.models import CommentCreate
from azure.devops.v5_1.work_item_tracking.models import Wiql
import html
import time
import glob
import mmap
import csv
import logging
import json
from migration import wit_client, wit_5_1_client, project
rtc_client = RTC.rtcclient

# global var for writing comments for attibutes
status_comments=[]

# create ads jpos object
def create_ads_jpos(jpo_from, jpo_op, jpo_path, jpo_value):
    jpo = JsonPatchOperation()
    jpo.from_ = jpo_from
    jpo.op = jpo_op
    jpo.path = jpo_path
    jpo.value = xstr(jpo_value)
    return jpo 

# merge two dicts
def Merge(dict_1, dict_2):
	result = dict_1 | dict_2
	return result

# link parent/child
def link_parent_child_ads(ads_child_id, ads_parent_url):
    print('link_parent_child_ads('+str(ads_child_id)+', '+str(ads_parent_url)+')')
    logging.info('link_parent_child_ads('+str(ads_child_id)+', '+str(ads_parent_url)+')')
    patch_document = []
    patch_document.append(
        JsonPatchOperation(
            op='add',
            path="/relations/-",
            value={
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": ads_parent_url
            }
        )
    )
    # give child_ads_id a parent link to parent_work_item
    try:
        wit_client.update_work_item(patch_document, ads_child_id)
        print('Gave ADS child '+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url))
        logging.info('Gave ADS child '+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url))
    except Exception as e:
        print("ADS Error linking ADS child: "+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url)+' . err='+str(e))
        logging.info("ADS Error linking ADS child: "+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url)+' . err='+str(e))

# Read local json map
def get_json_map(filename):
    json_map={}
    if(os.path.isfile(filename)):
        with open(filename, "r") as read_file:
            json_map = json.load(read_file)
    return json_map

# Check local json map file if work item has already been migrated
def check_json_map(rtc_id, rtc_type):

    rtc_type=format_rtc_type(rtc_type)
    
    print('check_json_map() check ' + str(rtc_type) + ' json map for ' + str(rtc_id)  )
    logging.info('check_json_map() check ' + str(rtc_type) + ' json map for ' + str(rtc_id)  )

    json_map_filename = rtc_type+'.json'
    json_map_filepath = CONFIG.json_maps_filepath +'\\'+ json_map_filename
    json_map = get_json_map(json_map_filepath)


    # check if rtc_id exists in json map
    if json_map.get(rtc_id) is not None:
        print('check_json_map() found it, returning now.')
        logging.info('check_json_map() found it, returning now.')
        return json_map.get(rtc_id)
    else:

        print('check_json_map() could not find, trying again this time by appending "story" to type ')
        logging.info('check_json_map() could not find, trying again this time by appending "story" to type ')

        json_map_filename = rtc_type+'story.json'
        json_map_filepath = CONFIG.json_maps_filepath +'\\'+ json_map_filename
        json_map = get_json_map(json_map_filepath)
        if json_map.get(rtc_id) is not None:
            return json_map.get(rtc_id)
        else:
            return None

# Add key/value object to local json map
def update_json_map(rtc_id, rtc_type, work_item_details):
    json_map_filename = rtc_type+'.json'
    json_map_filepath = CONFIG.json_maps_filepath +'\\'+ json_map_filename
    json_map=get_json_map(json_map_filepath)
    json_map[rtc_id]=work_item_details
    with open(json_map_filepath, 'w') as f:
        json.dump(json_map, f)

# fetch migrated ads id from corresponding json map
def get_ads_id(rtc_child_id, rtc_child_type):
    ads_id = None
    json_map_obj = check_json_map(rtc_child_id, rtc_child_type)
    if json_map_obj is not None:
        ads_id=json_map_obj['ads_id']
    return ads_id

# combine child data fetched from an rtcclient query with the rtc child data stored in local json map
def combine_rtc_child_info(children_rtc, json_map_children):
    combined=json_map_children
    # for each rtc child id in children_rtc:
    for rtc_id in children_rtc:
        # check if rtc_id exists in combined{}
        if combined.get(rtc_id) is None:
            # if it does not exist, add children_rtc[rtc_id] to combined
            combined[rtc_id] = children_rtc[rtc_id]
            # if it does exist, do nothing
    return combined

# get each file in filepath that ends with '_map.json'
def get_json_map_filepaths(directory='./'):
    filepaths=[]
    for file in os.listdir(directory):
        if file.endswith(".json"):
            filepaths.append(os.path.join(directory, file))
    return filepaths

# format mvp raw_data resource value
def get_xml_value_from_rtc(rtc_work_item={}, full_rtc_property_key=''):
    ads_value=''
    try:
        mvp_url = rtc_work_item.raw_data[full_rtc_property_key]['@rdf:resource']
        ads_value = rtc_client.getXmlField(mvp_url, "dc:title")
    except Exception as err:
        print('err:'+str(err))

    return ads_value

#enforce max 255 char limit
def char_limit_255(rtc_title, rtc_work_item={}, full_rtc_property_key=''):
    if len(rtc_title) > 255:
        rtc_title=rtc_title[ 0 : 252 ]
        rtc_title=rtc_title+"..."
    return rtc_title

# format title 
def format_title(rtc_title, rtc_work_item={}, full_rtc_property_key=''):
    ads_title = rtc_title

    #html string decode
    ads_title=html.unescape(ads_title)

    # if title includes link, remove link
    #'<a href="...url in title..">Setup teams structure and team areas</a>'
    if 'href=' in ads_title:
        #get everything after '>'
        ads_title=ads_title.split('>')[1]
        #get everything before '<'
        ads_title=ads_title.split('<')[0]
    return ads_title

# format ads iteration path
def format_ads_iteration_path(user_id='', rtc_work_item={}, full_rtc_property_key=''):
    iteration_path=''
    try:
        rtc_planned_for = rtc_work_item.plannedFor
        if rtc_planned_for is None:
            rtc_planned_for=''
        if rtc_planned_for.lower() == 'backlog' or rtc_planned_for.lower() == 'unassigned' or rtc_planned_for == '':
            iteration_path=CONFIG.ads_project_name
        else:
            if 'sprint' in rtc_planned_for.lower():
                pi_value = rtc_planned_for.split(' ')[1]
                #print("pi_value = "+pi_value)
                sprint_num_range = str(pi_value)+'-'+str(rtc_planned_for.split(' ')[3])
                #print("sprint_num_range = "+sprint_num_range)
                iteration_path = f"{CONFIG.ads_project_name}\PI{pi_value}\Sprint {sprint_num_range}"

            else:
                pi=rtc_planned_for.replace(' ', '')
                iteration_path = f"{CONFIG.ads_project_name}\{pi}"

        #print("iteration_path = "+iteration_path)

    except Exception as e:
        print(e)

    return iteration_path

# formatting for ads state
def format_ads_state(rtc_state='', rtc_work_item={}, full_rtc_property_key=''):
    ads_state=rtc_state
    rtc_ads_state_map = {
        'Ready':'New'
    }
    if rtc_state in rtc_ads_state_map:
        ads_state = rtc_ads_state_map[rtc_state]
    return ads_state

# formatting for ads area path
def format_ads_area_path(user_id='', rtc_work_item={}, full_rtc_property_key=''):
    projectarea_name = CONFIG.ads_project_name #RTC.ISD_Project_Area.title
    area_path_value=""

    #filed_against = rtc_work_item.filedAgainst
    #area_path_value = f"{projectarea_name}\{filed_against}"
    rtc_planned_for = rtc_work_item.plannedFor
    if rtc_planned_for == None:
        rtc_planned_for = ""
    
    #if rtc_planned_for.lower() == 'backlog' or rtc_planned_for.lower() == 'unassigned' or rtc_planned_for == '':
    #    area_path_value = projectarea_name
    #else:

    filed_against_url = rtc_work_item["raw_data"]["rtc_cm:filedAgainst"]['@rdf:resource']
    filed_against = rtc_client.getXmlField(filed_against_url, "rtc_cm:hierarchicalName")
    filed_against_val_split = filed_against.split('/')
    filed_against_val_split.pop(0)
    filed_against = "\\".join(filed_against_val_split)

    area_path_value = f"{projectarea_name}\{filed_against}"
    
    ## replace "EPIQ Affiniti Protego SW" with "Platform"
    area_path_value=area_path_value.replace('EPIQ Affiniti Protego SW', 'Platform')
    area_path_value=area_path_value.replace('EPIQ Affiniti HW', 'Platform')
    area_path_value=area_path_value.replace('OS and Install', 'OS Install')

    print(area_path_value)

    return area_path_value

# formatting for ADS 'size' work item var
def format_ads_size(rtc_size_var='', rtc_work_item={}, full_rtc_property_key=''):
    ads_size=0
    rtc_progress_url=rtc_work_item['raw_data']['rtc_cm:progressTracking']['@rdf:resource']
    rtc_progress_completed=rtc_client.getXmlField(rtc_progress_url, "oslc_pl:sizingUnitsCompleted")
    rtc_progress_remaining=rtc_client.getXmlField(rtc_progress_url, "oslc_pl:sizingUnitsRemaining")
    ads_size=int(rtc_progress_completed)+int(rtc_progress_remaining)
    return ads_size

# formatting for dc:creator
def format_ads_user(user_id='', rtc_work_item={}, full_rtc_property_key=''):
    user_email=''
    if user_id != '' and user_id != None:
        user_email = rtc_client.getUserEmail(user_id, CONFIG.RTC_URL)
    return user_email

# formatting for description
def format_description_header(rtc_description='', rtc_work_item={}, full_rtc_property_key=''):
    description_header = '<b> RTC ' + rtc_work_item.type + ' '+ rtc_work_item.identifier + ' : </b>' + rtc_work_item.title + ' <br/> <br/>'
    description = description_header
    if(rtc_work_item.description is not None):
        description += rtc_work_item.description
    return description

# ensure value is not greater then 255 chars, handle case where it is greater
def format_char_limit(rtc_value, rtc_work_item, full_rtc_property_key):
    new_rtc_value=rtc_value
    if len(new_rtc_value) > 254:
        new_rtc_value='RTC value too big for ADS, see comments for full value'
        comment_html='<b> RTC Property '+str(full_rtc_property_key)+' could not fit in field for '+str(rtc_work_item.type)+', so will instead be dislayed inside this comment: </b><br> '+str(rtc_value)
        #"<b>SIT Story Type 'Number of New Issues Found' Field is too large for ADS, and will instead be displayed inside this comment:</b><br> " + str(user_story_item.issues_found)
        status_comments.append(comment_html)
    return new_rtc_value

# ensure value is string
def format_string(rtc_value='', rtc_work_item={}, full_rtc_property_key=''):
    if rtc_value is None:
        return ''
    return str(rtc_value)

# map RTC priority int to ADS priority string
def format_ads_priority(rtc_value='', rtc_work_item={}, full_rtc_property_key=''):
    priority_str = rtc_work_item.priority.lower()
    priority_mappings = ['unassigned','low','medium','high']
    priority = priority_mappings.index(priority_str)+1
    return int(priority)

# format Story Type for ads
def format_ads_story_type(rtc_type, rtc_work_item={}, full_rtc_property_key=''):
    ads_value=rtc_type
    try:
        rtc_ads_map={
            'Technical Spike Story':'Technical Spike',
            'SIT Story':'SIT',
            'Defect Story':'Defect',
            'Enhancement Story':'Enhancement',
            'Specification Story':'Documentation',
            'Story':'Enhancement',
        }
        if rtc_type in rtc_ads_map:
            ads_value=rtc_ads_map[rtc_type]
    
    except Exception as e:
        print(e)

    if ads_value is '':
        print('empty')
    return ads_value

# format tags for ads ticket
def format_ads_tags(rtc_value='', rtc_work_item={}, full_rtc_property_key=''):
    tags=''
    # get config tags
    config_tags = CONFIG.tags
    tags += config_tags
    # get rtc tags
    if hasattr(rtc_work_item, 'subject'):
        if rtc_work_item['subject'] is not None:
            rtc_tags = ";"+ rtc_work_item.subject.replace( ',',';')
            tags += rtc_tags
    if hasattr(rtc_work_item, 'plannedFor'):
        if rtc_work_item['plannedFor'] is not None:
            rtc_tags =  ";RTC-PlannedFor:"+ rtc_work_item.plannedFor
            tags += rtc_tags
    return tags

# format RTC value to work for ADS (run through each formatting_function)
def format_rtc_ads(rtc_property_value, formatting_functions, rtc_work_item, full_rtc_property_key):
    formatted_value=rtc_property_value
    # for each formatting function name (string)
    for formatting_function_name in formatting_functions:
        # call function
        formatted_value=globals()[formatting_function_name](formatted_value, rtc_work_item, full_rtc_property_key)
    return formatted_value

# get rtc property value from rtc work item using rtc property key
def get_rtc_property_value(rtc_work_item, rtc_property_key, rtc_property, properties_obj):
    print('Get ' + str(rtc_property) + ' from rtc_work_item')
    logging.info('Get ' + str(rtc_property) + ' from rtc_work_item')
    rtc_property_value=None
    value_found=False
    # determine if we can get property from main values or if we need to use raw_data
    if hasattr(rtc_work_item, rtc_property_key):
        # retrieve rtc value
        rtc_property_value = rtc_work_item[rtc_property_key]
        value_found = True
    elif rtc_work_item.raw_data[rtc_property] is not None:
        rtc_property_value = get_xml_value_from_rtc(rtc_work_item, rtc_property)
        value_found=True

    if value_found:
        # run formatting functions (if needed) to convert RTC value to ADS
        if properties_obj[rtc_property].get('formatting') is not None:
            formatted_value = format_rtc_ads(
                rtc_property_value, 
                properties_obj[rtc_property].get('formatting'), 
                rtc_work_item,
                rtc_property
            )
        else:
            formatted_value = rtc_property_value

        return formatted_value
    
# extract all attributes from an rtc work item into a jpos[] list 
def convert_rtc_properties(rtc_work_item, properties_obj):
    jpos=[]
    # for each property:
    for property in properties_obj:
        # split property string by ':' char and only use first part
        rtc_property_key=property.split(':')[1].strip()
        # replace any '-' dash character with an underscore '_' character
        rtc_property_key=rtc_property_key.replace('-', '_')
        # get formatted rtc property value
        formatted_value = get_rtc_property_value(rtc_work_item, rtc_property_key, property, properties_obj)
        # get ads attribute path
        property_ads_path = properties_obj[property]['path']
        try:
            # if property_ads_path is not None, then there is an ADS location for migration (ex: type does not get migrated to a field)
            if property_ads_path is not None:
                # create ads jpos object and add it to a list 
                print('    adding: rtc_propety:' + str(rtc_property_key) + ", ads_path:" + str(property_ads_path) + ', ads_value:' + str(formatted_value))
                logging.info('    adding: rtc_propety:' + str(rtc_property_key) + ", ads_path:" + str(property_ads_path) + ', ads_value:' + str(formatted_value))
                ads_jpo = create_ads_jpos(
                    jpo_from=None, 
                    jpo_op="add", 
                    jpo_path=str(property_ads_path),
                    jpo_value=str(formatted_value)
                )
                jpos.append(ads_jpo)
           
        except Exception as e:
            print('Error = ',str(e), ', property_ads_path=',property_ads_path)
            logging.info('Error = ',str(e), ', property_ads_path=',property_ads_path)
    return jpos

# Setup and initialize log file 
def init_log_file(filename):
    init_dir(CONFIG.logging_filepath)
    logging.basicConfig(filename=filename, encoding='utf-8', level=logging.INFO)
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logging.info('\nBegin Epic migration '+dt_string)
    print('\nBegin Epic migration '+dt_string)

# Create folder if it does not already exist
def create_dir(dirname):
    if os.path.exists(dirname) is not True:
        os.mkdir(dirname)

# Delete folder if it exists, then create folder
def init_dir(dirname, delete=False):
    if delete:
        remove(dirname)
    if os.path.exists(dirname) is not True:
        os.mkdir(dirname)

def format_rtc_type(rtc_type):
    print('rtc_type='+str(rtc_type))
    # if rtc_type is url, get everything after last '.' char
    if 'https://' in rtc_type:
        rtc_type=rtc_type[rtc_type.rindex('.')+1:]

    return rtc_type.strip().lower().replace(' ','').replace('_','')

# migrate work item from rtc to ads
def migrate_work_item(rtc_work_item, logging, migrated_csv_filepath):
    rtc_id = rtc_work_item.identifier
    print('migrate_work_item() rtc_id='+str(rtc_id))
    logging.info('migrate_work_item() rtc_id='+str(rtc_id))
    

    rtc_url=rtc_work_item['url']
    rtc_type = format_rtc_type(rtc_work_item.type)

    # check if rtc type is valid
    if rtc_type.strip() == 'defect':
        print('item type not suported')
    else:
        print('not defect ')


        try:
            # if rtc_type is url, get everything after last '.' char
            if 'https://' in rtc_type:
                print('rtc_type included url: '+rtc_type)
                rtc_type=rtc_type[rtc_type.rindex('.')+1:]
            rtc_type = format_rtc_type(rtc_type)

            # work_item_status = 'found' or 'created'
            work_item_status=''

            # check if work item with this rtcid already exists in azure output project
            ads_work_item = get_ads_work_item_by_id(rtc_id, CONFIG.RTC_projectarea_name, wit_5_1_client)
            if ads_work_item is not None:
                print("work item already exists in ads")
                logging.info("work item already exists in ads")
                # create obj of work item details to write in JSON map file
                work_item_details = {
                    #'rtc_children':children_rtc,
                    'ads_id':str(ads_work_item.id),
                    'ads_url':str(ads_work_item.url),
                    'rtc_url':str(rtc_url),
                    'ads_info':{
                        "op": "add",
                        "path": "/relations/-",
                        "value": {
                            "rel": "System.LinkTypes.Hierarchy-Reverse",
                            "name": "Parent",
                            "url": ads_work_item.url
                        }
                    }
                }
                update_json_map(rtc_id, rtc_type, work_item_details)
                work_item_status='found'

            elif ads_work_item is None:
                print("work item does not already exists in ads")
                logging.info("work item does not already exists in ads")
                
                # get work item specific rtc properties list
                if rtc_type not in CONFIG.work_items_property_map:
                    # try adding 'story' to end
                    rtc_type=rtc_type+"story"
                
                if rtc_type in CONFIG.work_items_property_map:
                    work_item_properties = CONFIG.work_items_property_map[rtc_type]
                else:
                    print("Could not get properties from CONFIG.work_items_property_map for work item type: "+str(rtc_type)+'\n')
                    logging.error("Could not get properties from CONFIG.work_items_property_map for work item type: "+str(rtc_type)+'\n')

                # get common rtc properties list
                common_properties = CONFIG.work_items_property_map['common']
                
                # convert all RTC properties to ADS attributes [jpos]
                work_item_jpos = convert_rtc_properties(rtc_work_item, work_item_properties)
                common_jpos = convert_rtc_properties(rtc_work_item, common_properties)
                jpos = work_item_jpos + common_jpos
                
                # determine what type of ADS ticket to create
                ads_type=rtc_type
                if CONFIG.rtc_ads_type_map.get(rtc_type) is not None:
                    ads_type = CONFIG.rtc_ads_type_map[rtc_type]
                else:
                    ads_type=rtc_type

                # create ADS work item
                try:
                    created_ads_item = wit_client.create_work_item(
                        document = jpos,
                        project = project.id,
                        type = ads_type,
                        validate_only = CONFIG.validate_only,
                        bypass_rules = CONFIG.bypass_rules,
                        suppress_notifications = CONFIG.suppress_notifications
                    )
                    #created_work_items_count=created_work_items_count+1
                except Exception as e:
                    print("Error creating ADS work item: "+str(e)+'\n')
                    logging.error("Error creating ADS work item: "+str(e)+'\n')

                    if "field 'System.AreaPath" in str(e):
                        for jpo in jpos:
                            if 'System.AreaPath' in jpo.path:
                                print('Area Path Issue: ', jpo.value)
                                logStr = 'area path issue = '+jpo.value
                                logging.error(logStr)
                            
                    created_ads_item='err'

                if created_ads_item != 'err':
                        
                    # ensure folder 'CONFIG.work_item_filepath // RTC_type' exists
                    work_item_location = CONFIG.work_item_filepath +'\\'+ rtc_type
                    create_dir(work_item_location)

                    # add attachments
                    attachments = rtc_work_item.getAttachments()
                    add_attachments_to_ads(attachments, wit_5_1_client, wit_client, created_ads_item, work_item_location, project, rtc_type, logging)
                    
                    # combine comments from work item with comments from migration status run to add to migrated ads work item
                    status_comments=[]
                    work_item_comments = rtc_work_item.getComments()   
                    if work_item_comments is None:
                        work_item_comments=[]
                    comments = status_comments + work_item_comments
                    add_comments_to_ads(comments, wit_5_1_client, project, created_ads_item, logging)
                    
                    # create obj of work item details to write in JSON map file
                    work_item_details = {
                        #'rtc_children':children_rtc,
                        'ads_id':str(created_ads_item.id),
                        'ads_url':str(created_ads_item.url),
                        'rtc_url':str(rtc_url),
                        'ads_info':{
                            "op": "add",
                            "path": "/relations/-",
                            "value": {
                                "rel": "System.LinkTypes.Hierarchy-Reverse",
                                "name": "Parent",
                                "url": created_ads_item.url
                            }
                        }
                    }

                    # store migrated ticket in work_item_type json map 
                    update_json_map(rtc_id, rtc_type, work_item_details)
                    work_item_status='created'

                    print('ADS work item created: '+str(created_ads_item.url))
                    logging.info('ADS work item created: '+str(created_ads_item.url))

                    # add migrated/found work item to csv
                    csv_row = [
                        str(rtc_work_item.identifier), 
                        str(rtc_work_item.type), 
                        str(rtc_work_item.url), 
                        str(created_ads_item.id),
                        str(ads_type),
                        str(str(created_ads_item.url).replace("_apis/wit/workItems", "_workitems/edit")), 
                        str(work_item_status)
                    ]
                    write_row_csv(migrated_csv_filepath, [csv_row])
                    
                    print('csv info written. ')
                    logging.info('csv info written. ')

        except Exception as e:
            print("migrate_work_item() err: "+str(e)+'\n')
            logging.error("migrate_work_item() err: "+str(e)+'\n')

def get_ads_work_item_by_id(rtcid, team_project, work_item_tracking_client):
    try:
        #create query
        work_item_tracking_client = wit_5_1_client
        query  = "SELECT [System.Id], [System.WorkItemType], [System.Title], [System.AssignedTo], [System.State], [System.Tags] FROM workitems WHERE [System.TeamProject] = '"+ team_project + "' AND [Custom.RTCID] = '"+str(rtcid)+"'"
        #convert query str to wiql
        wiql = Wiql(query=query)
        #run query
        query_results = work_item_tracking_client.query_by_wiql(wiql).work_items
        print('get_ads_work_item_by_id() found '+str(len(query_results))+' results in ads query for rtcid='+str(rtcid))
        logging.info('get_ads_work_item_by_id() found '+str(len(query_results))+' results in ads query for rtcid='+str(rtcid))
        if len(query_results) == 0:
            return None

        elif len(query_results) == 1:
            work_item_id = query_results[0].id
            work_item = work_item_tracking_client.get_work_item(work_item_id)
            print('get_ads_work_item_by_id() found 1 result: '+str(work_item.url))
            logging.info('get_ads_work_item_by_id() found 1 result: '+str(work_item.url))
            return work_item

        elif len(query_results) > 1:
            print('get_ads_work_item_by_id() found 1+ results '+str(work_item.url))
            logging.error('get_ads_work_item_by_id() found 1+ results: '+str(work_item.url))
            return None

        #get the results via title
        #for item in query_results:
        #    work_item = work_item_tracking_client.get_work_item(item.id)
        #    pprint.pprint(work_item.fields['System.Title'])
    except Exception as e:
        print("get_ads_work_item_by_id() err = "+e)
        logging.error("get_ads_work_item_by_id() err = "+e)

# if string is None, return ''
def xstr(s):
    if s is None:
        return ''
    return str(s)

# get current time milliseconds
def current_milli_time():
    return round(time.time() * 1000)

# create csv file
def create_csv(csv_name, fieldnames):
    with open(csv_name, 'w+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

# write to csv file 
def write_row_csv(csv_name, rows):
    with open(csv_name, 'a', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

# write to html file
def write_html(filename, col_headers, rows, summary_str):
    # open file
    fileout = open(filename, "w")

    # create table html+style
    table = "<style>table, th, td{ border: 1px solid black; border-collapse: collapse; border-spacing: 8px; padding:7px } .header{ background-color: #3DBBDB; color:white; text-align: left; padding:7px } </style> <br><a>"+summary_str+"</a><br><hr><table>\n"

    # create the table's column headers
    table += "  <tr>\n"
    for column in col_headers:
        table += "    <th class='header'>{0}</th>\n".format(column.strip())
    table += "  </tr>\n"

    # Create the table's row data
    # rowData=['var1,var2,var3','xar1,xar2,xar3']
    for line in rows:
        row = line.split(",")
        table += "  <tr>\n"
        for column in row:
            item_html = ""
            if column.startswith("https://"):
                item_html="    <td><a href='{0}'>{0}</a></td>\n"
            else:
                item_html="    <td>{0}</td>\n"
            table += item_html.format(column.strip())
        table += "  </tr>\n"

    table += "</table>"

    fileout.writelines(table)
    fileout.close()

# Query RTC urls
def query_rtc_urls(work_item_type, urls, returned_properties_list, logging, query_client):
    queried_wis=[]
    query_count=1
    for query_url in urls:
        start_time = time.time()
        try:
            query_url = rchop(query_url, '&refresh=true')

            logging.info('Beginning RTC query for '+str(work_item_type)+': '+str(query_count)+'/'+str(len(urls))+' with '+str(len(returned_properties_list))+' properties: '+query_url)
            print('Beginning RTC query for '+str(work_item_type)+': '+str(query_count)+'/'+str(len(urls))+' with '+str(len(returned_properties_list))+' properties: '+query_url)
            returned_properties = ",".join(returned_properties_list)
            query_results = query_client.runSavedQueryByUrl(query_url, returned_properties=returned_properties)
            if query_results is None:
                query_results=[]

            duration=time.time() - start_time
            print('Found '+ str(len(query_results)) + ' results in ' + str(round(duration, 2)) +' seconds.')
            logging.info('Found '+ str(len(query_results)) + ' results in ' + str(round(duration, 2)) +' seconds.')
            queried_wis.extend(query_results)
        except Exception as e:
            print("Error running RTC query url: "+str(e))
            logging.error("Error running RTC query url: "+str(e))
        query_count=query_count+1
    return queried_wis

# Download and add attachments to ADS ticket
#                          (attachments, wit_5_1_client,wit_client, created_ads_item, rtc_work_item, project, rtc_type, logging)
def add_attachments_to_ads(attachments, azure_wit_5_1_client, azure_wit_client, azure_work_item, work_item_location, project, local_work_folder, logging):
    attachment_html="<b>RTC-ATTACHMENTS : </b> <br/>"
    if attachments is not None:
        for attachment in attachments:
            attachment_html += '<a href="'+attachment.url+'" >'+attachment.label+' </a>  by '+attachment.creator +' on '+attachment.created+'<br/>'

        azure_wit_5_1_client.add_comment(
            project=project.id,
            work_item_id=azure_work_item.id,
            request=CommentCreate(text=attachment_html)
        )

        remove(work_item_location)
        os.mkdir(work_item_location)
        for i in attachments:
            print("i=")
            print(i)

            if '\\' in i.description:
                filename=(i.description)[(i.description).rindex("\\")+1:]
            else:
                filename=i.description

            filepath = work_item_location +'\\'+ filename
            print("Saving attachment: "+str(filename))
            try:
                download_rtc_attachment(
                    i.url,
                    rtc_client,
                    filepath
                )
            except Exception as e:
                print("Error downloading attachment: "+str(e)+'\n')
                logging.error("Error downloading attachment: "+str(e)+'\n')
                
        files = glob.glob(os.getcwd() + '\\' +work_item_location+"\\*")
        for doc_path in files:
            print(doc_path)
            with open(doc_path, 'r+b') as file:
                # use mmap, so we don't load entire file in memory at the same time, and so we can start
                # streaming before we are done reading the file.
                mm = mmap.mmap(file.fileno(), 0)
                basename = os.path.basename(doc_path)
                attachment = azure_wit_client.create_attachment(mm, file_name=basename)
                                
                # Link Work Item to attachment
                patch_document = [
                    JsonPatchOperation(
                        op="add",
                        path="/relations/-",
                        value={
                            "rel": "AttachedFile",
                            "url": attachment.url
                        }
                    )
                ]

                azure_wit_client.update_work_item(
                    document = patch_document, 
                    id = azure_work_item.id,
                    project = project.id,
                    validate_only = CONFIG.validate_only,
                    bypass_rules = CONFIG.bypass_rules,
                    suppress_notifications = CONFIG.suppress_notifications
                )
            
# Add comments to ADS ticket
def add_comments_to_ads(comments, azure_wit_5_1_client, project, azure_work_item, logging):
    if comments is not None:
        for comment in comments:
            if type(comment) == str:
                comment_html=comment
            else:
                if comment.description is not None:
                    user_email = rtc_client.getUserEmail(comment.creator, CONFIG.RTC_URL)
                    comment_html="<b>RTC Comment By :</b> " + str(user_email) + "<b> RTC-TIMESTAMP : </b>" + str(comment.created) +'<br>'+ str(comment.description)
         
                

            try:
                azure_wit_5_1_client.add_comment(
                    project=project.id,
                    work_item_id=azure_work_item.id,
                    request=CommentCreate(text=comment_html)
                )
            except Exception as e:
                print("Error adding comment: "+str(e)+'\n')
                logging.error("Error adding comment: "+str(e)+'\n')
       
# param <path> could either be relative or absolute
def remove(path):
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains
    
def download_rtc_attachment(url, rtc_client, relative_filepath_and_name):
    print("download_rtc_attachment")
    invalid = '<>:"|?* '
    for char in invalid:
        relative_filepath_and_name = relative_filepath_and_name.replace(char, '')
        
    headers = rtc_client.headers
    headers['Accept']='text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'

    file = requests.get(url,headers=headers,allow_redirects=True,verify=False)
    with open(relative_filepath_and_name, 'wb') as f:
        f.write(file.content)

# if string is None, return ''
def xstr(s):
    if s is None:
        return ''
    return str(s)

# Remove substring from string if it exists at end
def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[:-len(suffix)]
    return s

# Feature Field: Planned For Implemented
def setPlannedForImplemented(feature_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.PlannedforImplemented"
    # get url of 'Planned For Implemented At RPM'
    url_val = feature_item.raw_data.get('rtc_cm:plannedFor')['@rdf:resource']
    # get value inside that URL
    jpo.value = xstr(rtc_client.getFeaturePlannedForValue(url_val))
    return jpo 

# Feature Field: Planned For Implemented At RPM
def setPlannedForImplementedRPM(feature_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.PlannedforImplementedRPM"
    # get url of 'Planned For Implemented At RPM'
    url_val = feature_item.raw_data.get('rtc_cm:Planned.for.at.RPM')['@rdf:resource']
    # get value inside that URL
    jpo.value = xstr(rtc_client.getFeaturePlannedForValue(url_val))
    return jpo 

# Feature Field: Planned For Done
def setPlannedForDone(feature_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.PlannedforDone"
    # get url of 'Planned For Implemented At RPM'
    url_val = feature_item.raw_data.get('rtc_cm:Planned.for.Done.Philips')['@rdf:resource']
    # get value inside that URL
    jpo.value = xstr(rtc_client.getFeaturePlannedForValue(url_val))
    return jpo 

# Feature Field: Planned For Done at RPM
def setPlannedForDoneRPM(feature_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.PlannedforDoneRPM"
    # get url of 'Planned For Implemented At RPM'
    url_val = feature_item.raw_data.get('rtc_cm:Planned.for.Done.at.RPM.Philips')['@rdf:resource']
    # get value inside that URL
    jpo.value = xstr(rtc_client.getFeaturePlannedForValue(url_val))
    return jpo 

def setDefectType(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.DefectType"
    jpo.value = xstr(rtc_work_item.defect)
    return jpo 

def setMVPStatus(rtc_work_item):
    mvp_url = rtc_work_item.raw_data['rtc_cm:MVP.list']['@rdf:resource']
    mvp_bool_str = rtc_client.getXmlField(mvp_url, "dc:title")
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.MVP"
    jpo.value = mvp_bool_str
    return jpo 

def setTeamTrack(rtc_work_item):
    #get teamtrack url
    team_track_url = rtc_work_item.raw_data['rtc_cm:TTboolean.philips']['@rdf:resource']
    team_track_bool = rtc_client.getXmlField(team_track_url, "dc:title")
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.TeamTrack"
    jpo.value = team_track_bool
    return jpo 

def setFoundInBuild(rtc_work_item):
    jpo = JsonPatchOperation()
    #jpo.from_ = None
    #jpo.op = "add"
    #jpo.path = "/fields/Custom.NumberofNewIssuesFound"
    #jpo.value = xstr(rtc_work_item.Number_of_New_Issues_Found)
    return jpo 

def setStoryType(story_type):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.StoryType"
    jpo.value = story_type
    return jpo 

def setSITNumberOfNewIssuesFound(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.NumberofNewIssuesFound"
    jpo.value = xstr(rtc_work_item.Number_of_New_Issues_Found)
    return jpo 

def setSITCart(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.Cart"
    jpo.value = xstr(rtc_work_item.cart_type)
    return jpo 

def setSITSystemTestArea(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.SystemTestArea"
    jpo.value = xstr(rtc_work_item.system_test_area)
    return jpo 

def setSITSerialNum(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.SystemSerialNumber"
    jpo.value = xstr(rtc_work_item.SystemSerialNumber)
    return jpo 

def setSITStoryIssues(issues_found_str):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.IssuesFound"
    jpo.value = issues_found_str
    return jpo

def setSITSubproductAttr(user_story_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.Subproduct"
    jpo.value = xstr(user_story_item.Sub_productAtt)
    return jpo

def getTitle(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add" 
    jpo.path = "/fields/System.Title"
    #html decode title
    title_str = rtc_work_item.title[:255]
    html_decoded_string = html.unescape(title_str)
    jpo.value = html_decoded_string
    return jpo 

def getDescription(rtc_work_item, descriptionHeader):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/System.Description"
    jpo.value = descriptionHeader
    if(rtc_work_item.description is not None):
        jpo.value += rtc_work_item.description
    return jpo

def getTargetedRelease(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Philips.Planning.Release"
    full_string = rtc_work_item.targeted_release
    jpo.value = full_string
    return jpo

def getAssignedTo(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/System.AssignedTo"
    #get user email from user id
    user_id = rtc_work_item.ownedBy
    user_email = rtc_client.getUserEmail(user_id, CONFIG.RTC_URL)
    jpo.value = user_email
    return jpo

def getModifiedBy(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/System.ChangedBy"
    jpo.value =rtc_work_item.modifiedBy + CONFIG.user_domain
    return jpo

def getCreator(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/System.CreatedBy"
    jpo.value =rtc_work_item.creator + CONFIG.user_domain
    return jpo

def getTags(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/System.Tags"
    jpo.value = CONFIG.tags
    if rtc_work_item.subject is not None:
        rtc_tags = ";"+ rtc_work_item.subject.replace( ',',';')
        jpo.value +=rtc_tags
    if rtc_work_item.plannedFor is not None:
        rtc_tags =  ";RTC-PlannedFor:"+ rtc_work_item.plannedFor
        jpo.value +=rtc_tags
    return jpo

def getComplexity(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Microsoft.VSTS.Scheduling.StoryPoints"
    full_string = rtc_work_item.raw_data['rtc_cm:com.ibm.team.apt.attribute.complexity']['@rdf:resource']
    split_data = full_string.split("complexity/")
    jpo.value = split_data[1]
    return jpo

def getPriority(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Microsoft.VSTS.Common.Priority"
    priority_str = rtc_work_item.priority.lower()
    priority_mappings = ['unassigned','low','medium','high']
    priority = priority_mappings.index(priority_str)+1
    jpo.value=priority
    return jpo

def getRTCID(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Custom.RTCID"
    full_string = rtc_work_item.raw_data.get('dc:identifier')
    jpo.value = full_string
    return jpo

def getSeverity(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Microsoft.VSTS.Common.Severity"
    jpo.value = rtc_work_item.severity
    return jpo

def getState(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/System.State"
    jpo.value = rtc_work_item.state
    return jpo


def getAcceptance(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Microsoft.VSTS.Common.AcceptanceCriteria"
    jpo.value = rtc_work_item.raw_data['rtc_cm:com.ibm.team.apt.attribute.acceptance']
    return jpo

def getResolution(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Microsoft.VSTS.Common.Resolution"
    jpo.value = rtc_work_item.resolution
    return jpo

def getTargetDate(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Microsoft.VSTS.Scheduling.TargetDate"  
    jpo.value = datetime.strptime(rtc_work_item.due[:19], '%Y-%m-%dT%H:%M:%S')
    return jpo

def getStartDate(rtc_work_item):
    jpo = JsonPatchOperation()
    jpo.from_ = None
    jpo.op = "add"
    jpo.path = "/fields/Microsoft.VSTS.Scheduling.StartDate"
    jpo.value = datetime.strptime(rtc_work_item.startDate[:19], '%Y-%m-%dT%H:%M:%S')
    return jpo
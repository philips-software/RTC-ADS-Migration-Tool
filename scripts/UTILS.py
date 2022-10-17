from threading import ExceptHookArgs
from tkinter import E
import CONFIG
import UTILS
import sys 
import shutil
import logging
import time
import json
import os
from datetime import datetime
from azure.devops.v5_0.work_item_tracking.models import JsonPatchOperation
from azure.devops.v5_1.work_item_tracking.models import Comment
from azure.devops.v5_1.work_item_tracking.models import CommentCreate
from azure.devops.v5_1.work_item_tracking.models import Wiql
import requests
import html
import mmap
import glob
import csv
import CREDENTIALS

def print_and_log(txt, error=False):
    print(txt)
    if error is True:
        logging.error(txt)
    else:
        logging.info(txt)

# Create and initialize log file 
def init_log_file(filename):
    # crate logging folder if it does not exit
    init_dir(CONFIG.logging_filepath)
    # init log file details
    logging.basicConfig(filename=filename, encoding='utf-8', level=logging.INFO)
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logging.info('\nMigration log file created '+dt_string)
    print('\nMigration log file created '+dt_string)

# Create folder if it does not exist. If delete var is specified as True, then delete folder if it exists before creating a new. 
def init_dir(dirname, delete=False):
    if delete:
        remove(dirname)
    if os.path.exists(dirname) is not True:
        os.mkdir(dirname)

# param <path> could either be relative or absolute
def remove(path):
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains

def init_rtc_connection():
    import RTC
    rtc_client = RTC.rtcclient
    rtc_query_client = rtc_client.query
    return rtc_client, rtc_query_client
        
def init_ads_connection():
    import AZURE
    ads_core_client = AZURE.core_client
    ads_wit_client = AZURE.wit_client
    ads_wit_5_1_client = AZURE.wit_5_1_client
    ads_project = ads_core_client.get_project(CREDENTIALS.ads_project_name)
    return ads_core_client, ads_wit_client, ads_wit_5_1_client, ads_project

def format_rtc_type(rtc_type):
    print('rtc_type='+str(rtc_type))
    # if rtc_type is url, get everything after last '.' char
    if 'https://' in rtc_type:
        rtc_type=rtc_type[rtc_type.rindex('.')+1:]

    return rtc_type.strip().lower().replace(' ','').replace('_','')

# Remove substring from string if it exists at end
def rchop(s, suffix):
    if suffix and s.endswith(suffix):
        return s[:-len(suffix)]
    return s

# Query RTC urls
def query_rtc_urls(work_item_type, urls, returned_properties_list, rtc_query_client):
    queried_wis=[]
    query_count=1
    for query_url in urls:
        start_time = time.time()
        try:
            query_url = rchop(query_url, '&refresh=true')
            print_and_log('Beginning RTC query for '+str(work_item_type)+': '+str(query_count)+'/'+str(len(urls))+' with '+str(len(returned_properties_list))+' properties: '+query_url)
            returned_properties = ",".join(returned_properties_list)
            query_results = rtc_query_client.runSavedQueryByUrl(query_url, returned_properties=returned_properties)
            if query_results is None:
                query_results=[]

            duration=time.time() - start_time
            print_and_log('Found '+ str(len(query_results)) + ' results in ' + str(round(duration, 2)) +' seconds.')
            queried_wis.extend(query_results)
        except Exception as e:
            print_and_log("Error running RTC query url: "+str(e),error=True)
        query_count=query_count+1
    return queried_wis

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
    print_and_log('check_json_map() check ' + str(rtc_type) + ' json map for ' + str(rtc_id)  )
    
    json_map_filename = rtc_type+'.json'
    json_map_filepath = CONFIG.json_maps_filepath +'\\'+ json_map_filename
    json_map = get_json_map(json_map_filepath)

    # check if rtc_id exists in json map
    if json_map.get(rtc_id) is not None:
        print_and_log('check_json_map() found it, returning now.')
        return json_map.get(rtc_id)
    else:
        print_and_log('check_json_map() could not find, trying again this time by appending "story" to type ')
        json_map_filename = rtc_type+'story.json'
        json_map_filepath = CONFIG.json_maps_filepath +'\\'+ json_map_filename
        json_map = get_json_map(json_map_filepath)
        if json_map.get(rtc_id) is not None:
            return json_map.get(rtc_id)
        else:
            return None

def get_ads_work_item_by_id(rtcid, team_project, ads_wit_5_1_client):
    try:
        #create query
        query  = "SELECT [System.Id], [System.WorkItemType], [System.Title], [System.AssignedTo], [System.State], [System.Tags] FROM workitems WHERE [System.TeamProject] = '"+ str(team_project) + "' AND [Custom.RTCID] = '"+str(rtcid)+"'"
        #convert query str to wiql
        wiql = Wiql(query=query)
        #run query
        query_results = ads_wit_5_1_client.query_by_wiql(wiql).work_items
        print_and_log('get_ads_work_item_by_id() found '+str(len(query_results))+' results in ads query for rtcid='+str(rtcid))
        
        if len(query_results) == 0:
            # no results found, return None
            return None
        else:
            work_item_id = query_results[0].id
            work_item = ads_wit_5_1_client.get_work_item(work_item_id)

            if len(query_results) == 1:
                # 1 result found, good
                print_and_log('get_ads_work_item_by_id() found 1 result: '+str(work_item.url))
                return work_item

            elif len(query_results) > 1:
                # more then 1 results found, bad
                print_and_log('get_ads_work_item_by_id() found 1+ results '+str(work_item.url))
                return 'multiple-results'

    except Exception as e:
        print_and_log("get_ads_work_item_by_id() err = "+str(e), error=True)

#################################################################
status_comments=[]
# format title 
def format_title(rtc_title, rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
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
def format_ads_iteration_path(user_id='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    iteration_path=''
    try:
        rtc_planned_for = rtc_work_item.plannedFor
        if rtc_planned_for is None:
            rtc_planned_for=''
        if rtc_planned_for.lower() == 'backlog' or rtc_planned_for.lower() == 'unassigned' or rtc_planned_for == '':
            iteration_path=CREDENTIALS.ads_project_name
        else:
            if 'sprint' in rtc_planned_for.lower():
                pi_value = rtc_planned_for.split(' ')[1]
                #print("pi_value = "+pi_value)
                sprint_num_range = str(pi_value)+'-'+str(rtc_planned_for.split(' ')[3])
                #print("sprint_num_range = "+sprint_num_range)
                iteration_path = f"{CREDENTIALS.ads_project_name}\PI{pi_value}\Sprint {sprint_num_range}"

            else:
                pi=rtc_planned_for.replace(' ', '')
                iteration_path = f"{CREDENTIALS.ads_project_name}\{pi}"

        #print("iteration_path = "+iteration_path)

    except Exception as e:
        print_and_log(e, error=True)

    return iteration_path

# formatting for ads state
def format_ads_state(rtc_state='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    ads_state=rtc_state
    rtc_ads_state_map = {
        'Ready':'New'
    }
    if rtc_state in rtc_ads_state_map:
        ads_state = rtc_ads_state_map[rtc_state]
    return ads_state

# formatting for ads area path
def format_ads_area_path(user_id='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    projectarea_name = CREDENTIALS.ads_project_name #RTC.ISD_Project_Area.title
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
    # now we have list of are apath values (without starting ads project area name)

    # add 
    filed_against = "\\".join(filed_against_val_split)

    area_path_value = f"{projectarea_name}\{filed_against}"
    
    '''
    # CV Workflow Area Path mappings
    area_path_value=area_path_value.replace('EPIQ Affiniti Protego SW', 'Epiq Affiniti')
    area_path_value=area_path_value.replace('EPIQ Affiniti HW', 'Epiq Affiniti')
    # ULT area path custom mapping
    area_path_value=area_path_value.replace('CV Workflow', 'CV')
    area_path_value=area_path_value.replace('\Epiq Affiniti\Harmony', '\Platform\Harmony')
    '''
    print_and_log(area_path_value)

    return area_path_value

# formatting for ADS 'size' work item var
def format_ads_size(rtc_size_var='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    ads_size=0
    rtc_progress_url=rtc_work_item['raw_data']['rtc_cm:progressTracking']['@rdf:resource']
    rtc_progress_completed=rtc_client.getXmlField(rtc_progress_url, "oslc_pl:sizingUnitsCompleted")
    rtc_progress_remaining=rtc_client.getXmlField(rtc_progress_url, "oslc_pl:sizingUnitsRemaining")
    ads_size=int(rtc_progress_completed)+int(rtc_progress_remaining)
    return ads_size

# formatting for dc:creator
def format_ads_user(user_id='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    user_email=''
    if user_id != '' and user_id != None:
        user_email = rtc_client.getUserEmail(user_id, CREDENTIALS.RTC_URL)
    return user_email

# formatting for description
def format_description_header(rtc_description='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    description_header = '<b> RTC ' + rtc_work_item.type + ' '+ rtc_work_item.identifier + ' : </b>' + rtc_work_item.title + ' <br/> <br/>'
    description = description_header
    if(rtc_work_item.description is not None):
        description += rtc_work_item.description
    return description

# ensure value is not greater then 255 chars, handle case where it is greater
def format_char_limit(rtc_value, rtc_work_item, full_rtc_property_key, rtc_client=None):
    new_rtc_value=rtc_value
    if len(new_rtc_value) > 254:
        new_rtc_value='RTC value too big for ADS, see comments for full value'
        comment_html='<b> RTC Property '+str(full_rtc_property_key)+' could not fit in field for '+str(rtc_work_item.type)+', so will instead be dislayed inside this comment: </b><br> '+str(rtc_value)
        #"<b>SIT Story Type 'Number of New Issues Found' Field is too large for ADS, and will instead be displayed inside this comment:</b><br> " + str(user_story_item.issues_found)
        status_comments.append(comment_html)
    return new_rtc_value

# ensure value is string
def format_string(rtc_value='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    if rtc_value is None:
        return ''
    return str(rtc_value)

# map RTC priority int to ADS priority string
def format_ads_priority(rtc_value='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    priority_str = rtc_work_item.priority.lower()
    priority_mappings = ['unassigned','low','medium','high']
    priority = priority_mappings.index(priority_str)+1
    return int(priority)

# format Story Type for ads
def format_ads_story_type(rtc_type, rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
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
        print_and_log(e, error=True)

    return ads_value

# format tags for ads ticket
def format_ads_tags(rtc_value='', rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
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

#enforce max 255 char limit
def char_limit_255(rtc_title, rtc_work_item={}, full_rtc_property_key='', rtc_client=None):
    if len(rtc_title) > 255:
        rtc_title=rtc_title[ 0 : 252 ]
        rtc_title=rtc_title+"..."
    return rtc_title


#################################################################

# format mvp raw_data resource value
def get_xml_value_from_rtc(rtc_client, rtc_work_item={}, full_rtc_property_key=''):
    ads_value=''
    try:
        mvp_url = rtc_work_item.raw_data[full_rtc_property_key]['@rdf:resource']
        ads_value = rtc_client.getXmlField(mvp_url, "dc:title")
    except Exception as err:
        print_and_log('err:'+str(err))

    return ads_value

# format RTC value to work for ADS (run through each formatting_function)
def format_rtc_ads(rtc_property_value, formatting_functions, rtc_work_item, full_rtc_property_key, rtc_client):
    formatted_value=rtc_property_value
    # for each formatting function name (string)
    for formatting_function_name in formatting_functions:
        # call function
        formatted_value=globals()[formatting_function_name](formatted_value, rtc_work_item, full_rtc_property_key, rtc_client)
    return formatted_value

# get rtc property value from rtc work item using rtc property key
def get_rtc_property_value(rtc_work_item, rtc_property_key, rtc_property, properties_obj, rtc_client):
    print_and_log('get_rtc_property_value() get ' + str(rtc_property) + ' from rtc_work_item')
    rtc_property_value=None
    value_found=False
    try:
        # determine if we can get property from main values or if we need to use raw_data
        if hasattr(rtc_work_item, rtc_property_key):
            # retrieve rtc value
            rtc_property_value = rtc_work_item[rtc_property_key]
            value_found = True
        elif rtc_work_item.raw_data[rtc_property] is not None:
            try:
                rtc_property_value = get_xml_value_from_rtc(rtc_client, rtc_work_item, rtc_property)
                value_found=True
            except Exception as e:
                print_and_log(e)
                rtc_property_value = get_xml_value_from_rtc(rtc_client, rtc_work_item, rtc_property)
                value_found=False

        if value_found is True:
            # run formatting functions (if needed) to convert RTC value to ADS
            if properties_obj[rtc_property].get('formatting') is not None:
                formatted_value = format_rtc_ads(
                    rtc_property_value, 
                    properties_obj[rtc_property].get('formatting'), 
                    rtc_work_item,
                    rtc_property,
                    rtc_client
                )
            else:
                formatted_value = rtc_property_value
            return formatted_value, 'found'

    except Exception as e:
        print_and_log(e)

    return None, 'notfound'

# if string is None, return ''
def xstr(s):
    if s is None:
        return ''
    return str(s)

def current_milli_time():
    return round(time.time() * 1000)

# create csv file
def create_csv(csv_name, fieldnames):
    with open(csv_name, 'w+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

# create ads jpos object
def create_ads_jpos(jpo_from, jpo_op, jpo_path, jpo_value):
    jpo = JsonPatchOperation()
    jpo.from_ = jpo_from
    jpo.op = jpo_op
    jpo.path = jpo_path
    jpo.value = xstr(jpo_value)
    return jpo 

# extract all attributes from an rtc work item into a jpos[] list 
def convert_rtc_attributes_csv_input(work_item_attribute_mappings, row, csv_cols, rtc_workitem, rtc_client):
    jpos=[]
    # for each attribute:
    for attribute in work_item_attribute_mappings:
        # get attribute name / value
        rtc_attribute_key=attribute
        rtc_attribute_value = row[csv_cols.index(rtc_attribute_key)]
        # get ads attribute path
        attribute_ads_path = work_item_attribute_mappings[attribute]['path']
        # call formatting function if needed
        if work_item_attribute_mappings[rtc_attribute_key].get('formatting') is not None:
            rtc_attribute_value = format_rtc_ads(
                rtc_attribute_value, 
                work_item_attribute_mappings[rtc_attribute_key].get('formatting'),
                row,
                csv_cols,
                rtc_workitem,
                rtc_attribute_key,
                rtc_client
            )

        # create jpo
        ads_jpo = create_ads_jpos(
            jpo_from=None, 
            jpo_op="add", 
            jpo_path=str(attribute_ads_path),
            jpo_value=str(rtc_attribute_value)
        )
        jpos.append(ads_jpo)

    return jpos

# extract all attributes from an rtc work item into a jpos[] list 
def convert_rtc_properties_query_input(rtc_work_item, properties_obj, rtc_client):
    jpos=[]
    # for each property:
    for property in properties_obj:
        # split property string by ':' char and only use first part
        rtc_property_key=property.split(':')[1].strip()
        # replace any '-' dash character with an underscore '_' character
        rtc_property_key=rtc_property_key.replace('-', '_')
        # get formatted rtc property value
        formatted_value, value_status = get_rtc_property_value(rtc_work_item, rtc_property_key, property, properties_obj, rtc_client)
        # get ads attribute path
        property_ads_path = properties_obj[property]['path']
        try:
            # if property_ads_path is not None, then there is an ADS location for migration (ex: type does not get migrated to a field)
            if property_ads_path is not None:
                # create ads jpos object and add it to a list 
                print_and_log('    adding: rtc_propety:' + str(rtc_property_key) + ", ads_path:" + str(property_ads_path) + ', ads_value:' + str(formatted_value))
                ads_jpo = create_ads_jpos(
                    jpo_from=None, 
                    jpo_op="add", 
                    jpo_path=str(property_ads_path),
                    jpo_value=str(formatted_value)
                )
                jpos.append(ads_jpo)
           
        except Exception as e:
            print_and_log('Error = '+str(e)+', property_ads_path='+property_ads_path, error=True)
    return jpos

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

# Download and add attachments to ADS ticket
def add_attachments_to_ads(attachments, azure_wit_5_1_client, azure_wit_client, azure_work_item, work_item_location, project, rtc_client):
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
def add_comments_to_ads(comments, azure_wit_5_1_client, project, azure_work_item,rtc_client):
    if comments is not None:
        for comment in comments:
            if type(comment) == str:
                comment_html=comment
            else:
                if comment.description is not None:
                    user_email = rtc_client.getUserEmail(comment.creator, CREDENTIALS.RTC_URL)
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
     
# Add key/value object to local json map
def update_json_map(rtc_id, rtc_type, work_item_details):
    json_map_filename = rtc_type+'.json'
    json_map_filepath = CONFIG.json_maps_filepath +'\\'+ json_map_filename
    json_map=get_json_map(json_map_filepath)
    json_map[rtc_id]=work_item_details
    with open(json_map_filepath, 'w') as f:
        json.dump(json_map, f)

# write to csv file 
def write_row_csv(csv_name, rows):
    with open(csv_name, 'a', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

# migrate work item from rtc to ads
def migrate_work_item(rtc_type, rtc_work_item, migration_results_csv_filepath, rtc_client, ads_wit_client, ads_project, ads_wit_5_1_client):
    migration_status=''
    rtc_id = rtc_work_item.identifier
    rtc_url=rtc_work_item['url']
    print_and_log('migrate_work_item() rtc_id='+str(rtc_id))

    # check local json map for work item type to see if rtcid exists, if so: do not migrate 
    if check_json_map(rtc_id, rtc_type) != None:
        print_and_log('rtc id exists inside json map, so do not migrate')
    else:
        print_and_log('item has not been migrated yet')
        
        # check azure project if work item matching rtcid property value exists, if so: do not migrate
        work_item_migration_status = get_ads_work_item_by_id(rtc_id, CREDENTIALS.ads_project_name, ads_wit_5_1_client)
        
        if work_item_migration_status == 'multiple-results':
            print_and_log('multiple results found in ADS for this RTCID')
            sys.exit(1)

        elif work_item_migration_status is not None:
            print_and_log("work item already exists in ads")
            # create obj of work item details to write in JSON map file
            work_item_details = {
                #'rtc_children':children_rtc,
                'ads_id':str(work_item_migration_status.id),
                'ads_url':str(work_item_migration_status.url),
                'rtc_url':str(rtc_url),
                'ads_info':{
                    "op": "add",
                    "path": "/relations/-",
                    "value": {
                        "rel": "System.LinkTypes.Hierarchy-Reverse",
                        "name": "Parent",
                        "url": work_item_migration_status.url
                    }
                }
            }
            update_json_map(rtc_id, rtc_type, work_item_details)
        
        elif work_item_migration_status is None:
            try:
                if rtc_type in CONFIG.work_items_property_map:
                    work_item_properties = CONFIG.work_items_property_map[rtc_type]
                else:
                    print_and_log("Could not get properties from CONFIG.work_items_property_map for work item type: "+str(rtc_type)+'\n')
                    sys.exit(1)

                # get common rtc properties list
                common_properties = CONFIG.work_items_property_map['common']
                
                # convert all RTC properties to ADS attributes [jpos]
                work_item_jpos = convert_rtc_properties_query_input(rtc_work_item, work_item_properties, rtc_client)
                common_jpos = convert_rtc_properties_query_input(rtc_work_item, common_properties, rtc_client)
                jpos = work_item_jpos + common_jpos
                
                # determine what type of ADS ticket to create
                ads_type=rtc_type
                if CONFIG.rtc_ads_type_map.get(rtc_type) is not None:
                    ads_type = CONFIG.rtc_ads_type_map[rtc_type]
                else:
                    ads_type=rtc_type

                # create ADS work item
                try:
                    created_ads_item = ads_wit_client.create_work_item(
                        document = jpos,
                        project = ads_project.id,
                        type = ads_type,
                        validate_only = CONFIG.validate_only,
                        bypass_rules = CONFIG.bypass_rules,
                        suppress_notifications = CONFIG.suppress_notifications
                    )
                    #created_work_items_count=created_work_items_count+1
                except Exception as e:
                    print_and_log("Error creating ADS work item: "+str(e)+'\n',error=True)
                    if "field 'System.AreaPath" in str(e):
                        for jpo in jpos:
                            if 'System.AreaPath' in jpo.path:
                                ads_wit_client('Area Path Issue: '+str(jpo.value),error=True)
                    created_ads_item='err'

                if created_ads_item != 'err':
                        
                    # ensure folder 'CONFIG.work_item_filepath // RTC_type' exists
                    work_item_location = CONFIG.work_item_filepath +'\\'+ rtc_type
                    init_dir(work_item_location)

                    # add attachments
                    attachments = rtc_work_item.getAttachments()
                    add_attachments_to_ads(attachments, ads_wit_5_1_client, ads_wit_client, created_ads_item, work_item_location, ads_project, rtc_client)
                    
                    # combine comments from work item with comments from migration status run to add to migrated ads work item
                    status_comments=[]
                    work_item_comments = rtc_work_item.getComments()   
                    if work_item_comments is None:
                        work_item_comments=[]
                    comments = status_comments + work_item_comments
                    add_comments_to_ads(comments, ads_wit_5_1_client, ads_project, created_ads_item, rtc_client)
                    
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

                    print_and_log('ADS work item created: '+str(created_ads_item.url))

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
                    write_row_csv(migration_results_csv_filepath, [csv_row])
                    
                    print_and_log('csv info written. ')
                    migration_status='migrated'

            except Exception as e:
                print_and_log("migrate_work_item() err: "+str(e)+'\n',error=True)
                migration_status='migration error'
            
    return migration_status

# get each file in filepath that ends with '_map.json'
def get_json_map_filepaths(directory='./'):
    filepaths=[]
    for file in os.listdir(directory):
        if file.endswith(".json"):
            filepaths.append(os.path.join(directory, file))
    return filepaths

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

# fetch migrated ads id from corresponding json map
def get_ads_id(rtc_child_id, rtc_child_type):
    ads_id = None
    json_map_obj = check_json_map(rtc_child_id, rtc_child_type)
    if json_map_obj is not None:
        ads_id=json_map_obj['ads_id']
    return ads_id

# link parent/child
def link_parent_child_ads(ads_child_id, ads_parent_url, ads_wit_client):
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
        ads_wit_client.update_work_item(patch_document, ads_child_id)
        print('Gave ADS child '+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url))
        logging.info('Gave ADS child '+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url))
    except Exception as e:
        print("ADS Error linking ADS child: "+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url)+' . err='+str(e))
        logging.info("ADS Error linking ADS child: "+str(ads_child_id)+' to ADS parent: '+str(ads_parent_url)+' . err='+str(e))

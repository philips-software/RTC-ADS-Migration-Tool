import CONFIG
import UTILS
import sys 
from csv import reader
import csv
import logging
import time
import json
import os
from datetime import datetime
from azure.devops.v5_0.work_item_tracking.models import JsonPatchOperation
from azure.devops.v5_1.work_item_tracking.models import Comment
from azure.devops.v5_1.work_item_tracking.models import CommentCreate
from azure.devops.v5_1.work_item_tracking.models import Wiql
import CREDENTIALS

# Init logging/work_items/json_maps dirs, and create log file
UTILS.init_log_file(CONFIG.logging_filepath +'\\'+CONFIG.logging_filename)  
UTILS.init_dir(CONFIG.work_item_filepath, delete=True)
UTILS.init_dir(CONFIG.json_maps_filepath, delete=False)

# Init migration results csv
timestamp=str(UTILS.current_milli_time())
migration_results_csv_filepath= CONFIG.logging_filepath+'\\'+'migrated_items_'+str(timestamp)+'.csv'
migrated_items_fieldnames = ['RTC ID', 'RTC Type', 'RTC URL', 'ADS ID', 'ADS Type', 'ADS URL', 'WORK ITEM STATUS']
UTILS.create_csv(
    migration_results_csv_filepath, 
    migrated_items_fieldnames
)

# Initialize RTC client connection
try:
    rtc_client, rtc_query_client = UTILS.init_rtc_connection()
except Exception as err:
    UTILS.print_and_log("Error logging into Azure, check your credentials inside CONFIG.py: "+str(err),error=True)
    sys.exit(1)

# Initialize ADS client connection
try:
    ads_core_client, ads_wit_client, ads_wit_5_1_client, ads_project = UTILS.init_ads_connection()
except Exception as err:
    UTILS.print_and_log("Error logging into RTC, check your credentials inside CONFIG.py: "+str(err),error=True)
    sys.exit(1)

# Determine input method 
if CONFIG.csv_input and CONFIG.rtc_query_url_input is True:
    UTILS.print_and_log("Both CONFIG.csv_input and CONFIG.rtc_query_url_input are true, please only select one.",error=True)
    sys.exit(1) 

# Migrate each RTC Query URL
if CONFIG.rtc_query_url_input is True:
    for rtc_query_type in CONFIG.rtc_query_urls:
        rtc_query_type_urls = CONFIG.rtc_query_urls[rtc_query_type]
        # if rtc query url type has urls
        if len(rtc_query_type_urls) > 0:
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # Query for list of RTC work items
            #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # get rtc query properties for this work item type (each property equals a value that rtcclient will query for, more properties==more time, seperating query urls by rtc work itemt ype ensures we dont waste time querying for feature-specific property values when querying epics)
            work_item_properties = None
            try:
                work_item_properties = CONFIG.work_items_property_map[UTILS.format_rtc_type(rtc_query_type)]
            except Exception as e:
                UTILS.print_and_log("Could not find RTC type "+str(UTILS.format_rtc_type(rtc_query_type))+" inside CONFIG.work_items_property_map. Skipping")
            
            if work_item_properties is not None:
                # get rtc common properties (title, description, etc which appear in every work item type)
                common_properties = CONFIG.work_items_property_map['common']
                # combine all property keys into one list (no duplicates)
                properties_list = list(work_item_properties.keys()) + list(common_properties.keys()) + CONFIG.default_rtc_properties
                # run query for rtc work items
                UTILS.print_and_log('running query now')
                query_results = UTILS.query_rtc_urls(rtc_query_type, rtc_query_type_urls, properties_list, rtc_query_client)
                #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                # Migrate each RTC work item in list
                #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                created_work_items_count = 0
                for rtc_work_item in query_results:
                    rtc_id = rtc_work_item.identifier
                    rtc_type = rtc_work_item['type']
                    rtc_url = rtc_work_item['url']
                    UTILS.print_and_log("Migrating " + str(rtc_type) + " RTC ID: " + str(rtc_id) + ". " + str(created_work_items_count) + "/" + str(len(query_results)) )
                    
                    #UTILS.print_and_log("work item does not exists in ads, so migrate it")
                    
                    # try to migrate work item
                    migration_status = UTILS.migrate_work_item(
                        UTILS.format_rtc_type(rtc_work_item.type),
                        rtc_work_item, 
                        migration_results_csv_filepath,
                        rtc_client,
                        ads_wit_client,
                        ads_project,
                        ads_wit_5_1_client
                    )
                    UTILS.print_and_log('migration_status = '+str(migration_status))

                    # migrate work item parent 
                    if CONFIG.migrate_parent is True:
                        try:
                            rtc_parent = rtc_work_item.getParent()
                            # if parent exists, and has not been migrated, migrate it
                            if rtc_parent is not None:
                                # try to migrate parent
                                migration_status = UTILS.migrate_work_item(
                                    UTILS.format_rtc_type(rtc_parent.type),
                                    rtc_parent, 
                                    migration_results_csv_filepath,
                                    rtc_client,
                                    ads_wit_client,
                                    ads_project,
                                    ads_wit_5_1_client
                                )
                                UTILS.print_and_log('migrated parent')
                        except Exception as e:
                            UTILS.print_and_log("Error getting work item parent: "+str(e)+'\n',error=True)

                    
                    # migrate work item children
                    if CONFIG.migrate_children is True:
                        try:
                            rtc_children = rtc_work_item.getChildren()
                            # if children were found
                            if rtc_children is not None:
                                # for each child
                                child_num = 0
                                for rtc_child in rtc_children:
                                    rtc_child_id=rtc_child.identifier
                                    UTILS.print_and_log('examining child rtc id: ' + str(rtc_child_id) + ', ' + str(child_num) + "/" + str(len(rtc_children)))
                                    # try to migrate  
                                    migration_status = UTILS.migrate_work_item(
                                        UTILS.format_rtc_type(rtc_child.type),
                                        rtc_child, 
                                        migration_results_csv_filepath,
                                        rtc_client,
                                        ads_wit_client,
                                        ads_project,
                                        ads_wit_5_1_client
                                    )
                                    child_num=child_num+1

                                    # migrate children of children
                                    if CONFIG.migrate_children_of_children is True:
                                        rtc_more_children = rtc_child.getChildren()
                                        more_child_num = 0
                                        for rtc_more_child in rtc_more_children:
                                            UTILS.print_and_log('examining child or child. id=' + str(rtc_more_child.identifier) + ', ' + str(more_child_num) + "/" + str(len(rtc_more_children)))
                                            # try to migrate  
                                            migration_status = UTILS.migrate_work_item(
                                                UTILS.format_rtc_type(rtc_more_child.type),
                                                rtc_more_child, 
                                                migration_results_csv_filepath,
                                                rtc_client,
                                                ads_wit_client,
                                                ads_project,
                                                ads_wit_5_1_client
                                            )
                        except Exception as e:
                            UTILS.print_and_log("Error getting work item children: "+str(e)+'\n',error=True)

# Migrate csv file input (Download from RTC, select all columns)
if CONFIG.csv_input is True:
    try:
        # open csv file 
        csv_row_count=0
        created_ads_item_count=0
        with open(CONFIG.csv_filepath, 'r', encoding='utf-16') as read_obj:
            # pass the file object to reader() to get the reader object
            csv_reader = reader(read_obj, delimiter='\t')
            # Iterate over each row in the csv using reader object
            csv_cols = None
            for row in csv_reader:
                # row variable is a list that represents a row in csv
                if csv_cols is None:
                    csv_cols = row 
                    UTILS.print_and_log('csv_cols=',csv_cols)
                    continue 
                else:
                    UTILS.print_and_log('___found '+str(len(row))+" items ___")
                    UTILS.print_and_log(row)
                    UTILS.print_and_log('________')
                    # get rtc row common info
                    rtc_id = row[csv_cols.index("Id")]
                    rtc_type = row[csv_cols.index("Type")]
                    # query rtc for work item info
                    myquerystr = 'dc:id="'+str(rtc_id)+'"'
                    returned_prop = "rtc_cm:modifiedBy,rtc_cm:ownedBy,dc:subject,rtc_cm:plannedFor,rtc_cm:filedAgainst,dc:created,dc:creator,dc:type"
                    queried_wis = rtc_query_client.queryWorkitems(query_str=myquerystr, projectarea_name=CREDENTIALS.RTC_projectarea_name, returned_properties=returned_prop)
                    rtc_workitem = queried_wis[0]    
                    # get common attribute mapping
                    common_attribute_mappings = CONFIG.csv_attribute_mappings['common']
                    # get work item attribute mappings
                    work_item_attribute_mappings = CONFIG.csv_attribute_mappings[rtc_type]
                    # create jpos for each attribute
                    common_jpos = UTILS.convert_rtc_attributes_csv_input(common_attribute_mappings, row, csv_cols, rtc_workitem, rtc_client)
                    work_item_attribute_jpos = UTILS.convert_rtc_attributes_csv_input(work_item_attribute_mappings, row, csv_cols, rtc_workitem, rtc_client)
                    # get jpos for work item
                    jpos = work_item_attribute_jpos + common_jpos
                    # create ads work item
                    ads_type=rtc_type
                    try:
                        created_ads_item = ads_wit_client.create_work_item(
                            document = jpos,
                            project = ads_project.id,
                            type = ads_type,
                            validate_only = CONFIG.validate_only,
                            bypass_rules = CONFIG.bypass_rules,
                            suppress_notifications = CONFIG.suppress_notifications
                        )
                    except Exception as e:
                        UTILS.print_and_log("Error creating ADS work item: "+str(e)+'\n',error=True)
                        continue
                UTILS.print_and_log("created work item: "+ created_ads_item.url)
                # ensure folder 'CONFIG.work_item_filepath // rtc_type' exists
                work_item_location = CONFIG.work_item_filepath +'\\'+ rtc_type
                UTILS.init_dir(work_item_location)

                # add attachments
                attachments = rtc_workitem.getAttachments()
                UTILS.add_attachments_to_ads(attachments, ads_wit_5_1_client, ads_wit_client, created_ads_item, work_item_location, ads_project, rtc_client)
                UTILS.print_and_log("added attachments")
                # add comments
                work_item_comments = rtc_workitem.getComments()   
                if work_item_comments is None:
                    work_item_comments=[]
                UTILS.add_comments_to_ads(work_item_comments, ads_wit_5_1_client, ads_project, created_ads_item, rtc_client)
                # get status_comments from newUtils
                status_comments = UTILS.status_comments
                if status_comments != []:
                    UTILS.add_comments_to_ads(work_item_comments, ads_wit_5_1_client, ads_project, created_ads_item, rtc_client)
                UTILS.print_and_log("added comments")
                # create obj of work item details to write in JSON map file
                work_item_details = {
                    #'rtc_children':children_rtc,
                    'ads_id':str(created_ads_item.id),
                    'ads_url':str(created_ads_item.url),
                    'rtc_url':str(rtc_workitem.url),
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
                UTILS.update_json_map(rtc_id, rtc_type, work_item_details)
                UTILS.print_and_log("updated json map: "+ rtc_type)
                # add to json
                UTILS.print_and_log('finished this work item')
                created_ads_item_count+=1
            csv_row_count+=1
        UTILS.print_and_log("Finished creating ADS work items based on csv file. \ncsv_row_count="+str(csv_row_count-1)+"\ncreated_ads_item_count="+str(created_ads_item_count))

    except Exception as err:
        UTILS.print_and_log(str(err),error=True)

# Link all work items in Azure ( parent / child links )
# for each '*.json' file in local directory
json_map_filepaths = UTILS.get_json_map_filepaths(CONFIG.json_maps_filepath)
for filepath in json_map_filepaths:
    print("Looking through each work item in json file: "+str(filepath))
    # get json map from filepath
    json_map = UTILS.get_json_map(filepath)
    # for each parent key/value pair
    for rtc_parent_id in json_map:
        print('rtc_parent_id = '+str(rtc_parent_id))
        unreachable_children=[]
        parent_json_map_obj = json_map[rtc_parent_id]
        
        # get rtc work item type from filepath
        rtc_parent_type = filepath.split('\\')[-1].replace('.json', '')
        print('rtc_parent_type = '+str(rtc_parent_type))

        # get children for rtc id
        try:
            children_rtc = rtc_client.getChildrenInfo(rtc_parent_id, CREDENTIALS.RTC_URL)
        except Exception as e:
            print("Could not get children for rtc item: "+str(rtc_parent_id))
            logging.error("Could not get children for rtc item: "+str(rtc_parent_id))
            children_rtc=None

        if children_rtc == None or children_rtc == []:
            children_rtc={}
        # get already children from json map
        json_map_children = {}
        if parent_json_map_obj.get('rtc_children') is not None:
            json_map_children = parent_json_map_obj.get('rtc_children')
        # combine the most recent rtc getChildren query with child results found in the map file
        current_rtc_children_status = UTILS.combine_rtc_child_info(children_rtc, json_map_children)
        # go through each rtc child id
        new_links_count=0
        for rtc_child_id in current_rtc_children_status:
            # get rtc work item type for child
            rtc_child_type=current_rtc_children_status[rtc_child_id]['type']
            # if it is not already linked:
            if current_rtc_children_status[rtc_child_id].get('linked') is None:
                # get migrated child ads id
                ads_child_id = UTILS.get_ads_id(rtc_child_id, rtc_child_type)
                # link parent/child if ads_child_id exists
                if ads_child_id is not None:
                    UTILS.link_parent_child_ads(ads_child_id, parent_json_map_obj['ads_url'], ads_wit_client)
                    # update current_rtc_children_status
                    current_rtc_children_status[rtc_child_id]['linked']=True
                    new_links_count+=1
                else:
                    print('Could not find rtc id '+str(rtc_child_id) + ' type='+str(rtc_child_type) +' in their local json map, so link could not be made' )
                    logging.info('Could not find rtc id '+str(rtc_child_id) + ' type='+str(rtc_child_type) +' in their local json map, so link could not be made' )
                    unreachable_children.append(str(rtc_child_id))
            else:
                print('already linked')
                logging.info('already linked')
        # write current_rtc_children_status to json if changes were made
        if new_links_count > 0:
            parent_json_map_obj['rtc_children']=current_rtc_children_status
            UTILS.update_json_map(rtc_parent_id, rtc_parent_type, parent_json_map_obj)

        #['RTC ID', 'RTC Type', 'RTC URL', 'ADS URL', 'RTC Unreachable Children', '# RTC Unreachable Children']
        #if there are unreachable children, for each unreachable child, find out 
        '''
        csv_row = [
            str(rtc_parent_id), 
            str(rtc_parent_type), 
            str(parent_json_map_obj['ads_url']), 
            str(parent_json_map_obj['rtc_url']),  
            str(','.join(unreachable_children)), 
            str(len(unreachable_children))
        ]
        UTILS.write_row_csv(migrated_hierarchy_csv_filepath, [csv_row])
        '''

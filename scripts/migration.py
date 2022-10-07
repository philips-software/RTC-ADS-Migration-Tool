import CONFIG
import UTILS
import sys 
import logging
import time
import json
import os
from datetime import datetime
from azure.devops.v5_0.work_item_tracking.models import JsonPatchOperation
from azure.devops.v5_1.work_item_tracking.models import Comment
from azure.devops.v5_1.work_item_tracking.models import CommentCreate
from azure.devops.v5_1.work_item_tracking.models import Wiql
import html

# get time when this script begins
start_time = time.time()

# Setup and initialize log file / local work items folder
UTILS.init_log_file(CONFIG.logging_filepath +'\\'+'migration.log')  
UTILS.init_dir(CONFIG.work_item_filepath, delete=True)
UTILS.init_dir(CONFIG.json_maps_filepath, delete=False)

# Initialize RTC client connection
try:
    import RTC
    rtc_client = RTC.rtcclient
    query_client = rtc_client.query
except:
    print("Error logging into RTC, check your credentials")
    logging.error("Error logging into RTC, check your credentials")
    sys.exit(1)

# Initialize ADS client connection
try:
    import AZURE
    core_client = AZURE.core_client
    wit_client = AZURE.wit_client
    wit_5_1_client = AZURE.wit_5_1_client
    project = core_client.get_project(CONFIG.ads_project_name)
except:
    print("Error logging into Azure, check your credentials")
    logging.error("Error logging into Azure, check your credentials")
    sys.exit(1)

# Create migrated_items.csv
timestamp=str(CONFIG.current_milli_time())
migrated_csv_filepath= CONFIG.logging_filepath+'\\'+'migrated_items_'+str(timestamp)+'.csv'
migrated_items_fieldnames = ['RTC ID', 'RTC Type', 'RTC URL', 'ADS ID', 'ADS Type', 'ADS URL', 'WORK ITEM STATUS']
UTILS.create_csv(
    migrated_csv_filepath, 
    migrated_items_fieldnames
)

########################################
# BEGIN WORK ITEM MIGRATION
########################################

# Run RTC queries for each work item type using appropriate properties 
for work_item_type in CONFIG.rtc_query_urls:
    work_item_urls = CONFIG.rtc_query_urls[work_item_type]
    if len(work_item_urls) > 0:
        # get work item specific rtc properties list
        if work_item_type not in CONFIG.work_items_property_map:
            # try adding 'story' to end
            work_item_type=work_item_type+"story"

        work_item_properties = CONFIG.work_items_property_map[UTILS.format_rtc_type(work_item_type)]
        # get common rtc properties list
        common_properties = CONFIG.work_items_property_map['common']
        # combine all property keys into one list (no duplicates)
        properties_list = list(work_item_properties.keys()) + list(common_properties.keys()) + CONFIG.default_rtc_properties
        # run query
        query_results = UTILS.query_rtc_urls(
            work_item_type,
            work_item_urls, 
            properties_list, 
            logging, 
            query_client
        )
        # migrate all queried RTC work items
        created_work_items_count = 0
        for rtc_work_item in query_results:
            # get rtc work item info
            rtc_id = rtc_work_item.identifier
            rtc_type = UTILS.format_rtc_type(rtc_work_item['type'])
            rtc_url=rtc_work_item['url']

            print("Migrating " + str(rtc_type) + " RTC ID: " + str(rtc_id) + ". " + str(created_work_items_count) + "/" + str(len(query_results)) )
            logging.info("Migrating " + str(rtc_type) + " RTC ID: " + str(rtc_id) + ". " + str(created_work_items_count) + "/" + str(len(query_results)) )                

            # check work_item_type json map if ticket has already been migrated
            if UTILS.check_json_map(rtc_id, rtc_type) != None:
                print('item has already been migrated, so break out of loop')
                logging.info('item has already been migrated, so break out of loop')
                continue 
            else:
                print('item has not been migrated yet')
                logging.info('item has not been migrated yet')

            UTILS.migrate_work_item(rtc_work_item, logging, migrated_csv_filepath)
            created_work_items_count+=1

            print('migrated work item')
            logging.info('migrated work item')
            
            # get rtc parent
            try:
                rtc_parent = rtc_work_item.getParent()
                # if parent exists, and has not been migrated, migrate it
                if rtc_parent is not None:
                    if UTILS.check_json_map(rtc_parent.identifier, rtc_parent.type) == None:
                        print('work item has a parent which has not been migrated yet, so migrate it')
                        logging.info('work item has a parent which has not been migrated yet, so migrate it')
                        # migrate it 
                        UTILS.migrate_work_item(rtc_parent, logging, migrated_csv_filepath)
                        print('migrated parent')
                        logging.info('migrated parent')
            
            except Exception as e:
                print("Error getting work item parent: "+str(e)+'\n')
                logging.error("Error getting work item parent: "+str(e)+'\n')

            # get rtc children
            try:
                rtc_children = rtc_work_item.getChildren()
                # if children were found
                if rtc_children is not None:
                    # for each child
                    child_num = 0
                    for rtc_child in rtc_children:
                        rtc_child_id=rtc_child.identifier
                        print('examining child rtc id: ' + str(rtc_child_id) + ', ' + str(child_num) + "/" + str(len(rtc_children)))
                        logging.info('examining child rtc id: ' + str(rtc_child_id) + ', ' + str(child_num) + "/" + str(len(rtc_children)))
                        # check if child has already been migrated
                        if UTILS.check_json_map(rtc_child.identifier, rtc_child.type) == None:
                            print('child has not been migrated yet, so migrate it')
                            logging.info('child has not been migrated yet, so migrate it')
                            # migrate it 
                            UTILS.migrate_work_item(rtc_child, logging, migrated_csv_filepath)
                            print('migrated child ')
                            logging.info('migrated child ')
                        else:
                            print('child has already been migrated')
                            logging.info('child has already been migrated')
                        child_num=child_num+1

                        # get children for this child
                        rtc_more_children = rtc_child.getChildren()
                        more_child_num = 0
                        for rtc_more_child in rtc_more_children:
                            print('examining child or child. id=' + str(rtc_more_child.identifier) + ', ' + str(more_child_num) + "/" + str(len(rtc_more_children)))
                            logging.info('examining child or child. id=' + str(rtc_more_child.identifier) + ', ' + str(more_child_num) + "/" + str(len(rtc_more_children)))
                        
                            # check if child has already been migrated
                            if UTILS.check_json_map(rtc_more_child.identifier, rtc_more_child.type) == None:
                                UTILS.migrate_work_item(rtc_more_child, logging, migrated_csv_filepath)
                            more_child_num=more_child_num+1

            except Exception as e:
                print("Error getting work item children: "+str(e)+'\n')
                logging.error("Error getting work item children: "+str(e)+'\n')

        created_work_items_count='temp-empty'
        print('Finished '+str(work_item_type)+' migration. ' + str(created_work_items_count) + ' ADS tickets created, ' + str(len(query_results)) + ' RTC items were queried.')
        logging.info('Finished '+str(work_item_type)+' migration. ' + str(created_work_items_count) + ' ADS tickets created, ' + str(len(query_results)) + ' RTC items were queried.')
 
########################################
# BEGIN WORK ITEM HIERARCHY LINKING
# At this point all work items should be migrated, now we will try to link parent/child relationships between ADS migrated work items
########################################

# create csv
migrated_hierarchy_fieldnames = ['RTC ID', 'RTC Type', 'RTC URL', 'ADS URL', 'RTC Unreachable Children', '# RTC Unreachable Children']
migrated_hierarchy_csv_filepath= CONFIG.logging_filepath+'\\'+'migrated_hierarchy_'+str(timestamp)+'.csv'
UTILS.create_csv(migrated_hierarchy_csv_filepath, migrated_hierarchy_fieldnames)

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
            children_rtc = rtc_client.getChildrenInfo(rtc_parent_id, CONFIG.RTC_URL)
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
                    UTILS.link_parent_child_ads(ads_child_id, parent_json_map_obj['ads_url'])
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
        csv_row = [
            str(rtc_parent_id), 
            str(rtc_parent_type), 
            str(parent_json_map_obj['ads_url']), 
            str(parent_json_map_obj['rtc_url']),  
            str(','.join(unreachable_children)), 
            str(len(unreachable_children))
        ]
        UTILS.write_row_csv(migrated_hierarchy_csv_filepath, [csv_row])

duration=time.time() - start_time
print('Finished script, total time length='+str(round(duration, 2)) +' seconds.')
logging.info('Finished script, total time length='+str(round(duration, 2)) +' seconds.')
        
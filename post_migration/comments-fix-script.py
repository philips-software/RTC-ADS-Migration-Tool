from csv import reader
import csv
import pandas as pd
import codecs
import CONFIG
import sys 
import logging
import time
import json
import os
from datetime import datetime
from azure.devops.v5_0.work_item_tracking.models import JsonPatchOperation
from azure.devops.v5_1.work_item_tracking.models import Comment
from azure.devops.v5_1.work_item_tracking.models import CommentCreate

# Setup and initialize log file 
def init_log_file(filename):
    logging.basicConfig(filename=filename, encoding='utf-8', level=logging.INFO)
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    logging.info('\nBegin Epic migration '+dt_string)
    print('\nBegin Epic migration '+dt_string)
# setup logging
init_log_file(CONFIG.logging_filepath +'\\'+'comments_fix.log')  

# Initialize ADS client connection
try:
    import AZURE
    core_client = AZURE.core_client
    wit_client = AZURE.wit_client
    wit_5_1_client = AZURE.wit_5_1_client
    project = core_client.get_project(CREDENTIALS.ads_project_name)
except:
    print("Error logging into Azure, check your credentials")
    logging.error("Error logging into Azure, check your credentials")
    sys.exit(1)

# read in csv as map
csv_filepath='FRUPS 9.8.2022.csv'
csv_map={}
with open(csv_filepath, 'r', encoding='utf-16') as read_obj:
    csv_reader = reader(read_obj, delimiter='\t')
    csv_cols = None
    for row in csv_reader:
        if csv_cols is None:
            csv_cols = row 
            csv_map['cols']=csv_cols
        else:
            row_map={}
            for csv_col in csv_cols:
                row_map[csv_col] = row[csv_cols.index(csv_col)]
            rtc_id = row[csv_cols.index("Id")]
            csv_map[rtc_id]=row_map

# begin 
filepath="FRUPS.json"
# read JSON file
f = open(filepath)
data = json.load(f)
f.close()
# for each parent
for rtc_parent_id in data:
    json_obj = data[rtc_parent_id]
    azure_parent_id = json_obj['ads_id']
    
    #azure_parent_id=67407
    
    print('azure_parent_id = '+str(azure_parent_id))
    # ------------------------------
    # DELETE ALL COMMENTS I CREATED
    # ------------------------------
    # get comments
    comments=wit_5_1_client.get_comments(
        project=project.id,
        work_item_id=int(azure_parent_id), 
        top=None, 
        continuation_token=None, 
        include_deleted=None, 
        expand=None, 
        order=None
    )
    print('comments count: '+str(comments.total_count))
    current_comment=0
    # for each comment on ads work item
    for comment in comments.comments:
        print('comment '+str(current_comment)+'/'+str(comments.total_count))
        print('id = '+str(comment.id)+'\ntext=\n-------------\n'+comment.text+'\n-------------')
        # if comment is one we created for too big field:
        if "could not fit in field for FRUPS(255" in comment.text:
            print('comment was created due to large field ')
            # delete comment 
            delete_comment_rsp = wit_5_1_client.delete_comment(
                project=project.id, 
                work_item_id=int(azure_parent_id), 
                comment_id=int(comment.id)
            )
            print('deleted comment: ')
            print(delete_comment_rsp)
            # check for value 'RTC value too big for ADS, see comments for full value' ON WORK ITEM
        current_comment+=1

    #
    # ADD BACK ANY FIELDS TOO BIG 
    #
    
    # get azure work item values
    ads_work_item=wit_5_1_client.get_work_item(
        id=int(azure_parent_id),
        project=project.id,
        fields=None, 
        as_of=None, 
        expand=None
    )
    # for each ADS field
    for field_key in ads_work_item.fields:
            field_value=ads_work_item.fields[field_key]
            if field_key.startswith('Custom.'):
                print(field_key + ' - ' + str(field_value))
                if "RTC value too big for ADS, see comments for full value" in str(field_value):
                    print('value was too big and should be a comment')
                    print(field_key)
                    # get rtc attribute title (ads name : rtc name)
                    field_name_mappings={
                        'Custom.AffectedProductFamilies':'System Usage',
                        'Custom.ProblemStatement':'Problem Statement'
                    }
                    rtc_val_title=field_name_mappings[field_key]
                    # get rtc field full value
                    rtc_val=csv_map[str(rtc_parent_id)][rtc_val_title]
                    # create comment text
                    comment_html='<b> RTC Property '+str(rtc_val_title)+' could not fit in ADS field '+str(field_key)+' because it was over 255 characters. The full value will be displayed inside this comment: </b><br> '+str(rtc_val)
        
                    # add 
                    wit_5_1_client.add_comment(
                        project=project.id,
                        work_item_id=int(azure_parent_id), 
                        request=CommentCreate(text=comment_html)
                    )
                    print('comment added')



    

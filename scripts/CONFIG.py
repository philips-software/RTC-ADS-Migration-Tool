###################################
# RTC / Azure DevOps credentials
###################################
# RTC Login Credentials
RTC_USERNAME = ""   
RTC_PASSWORD = "" 
# Azure DevOps Personal Access Token
personal_access_token = ""

###################################
# RTC Input location
###################################
RTC_URL = ""                      # https://rtc.mycompany.com/ccm
RTC_projectarea_name = ""         # "Project Area Name"             
# RTC users email domain 
user_domain = ""                  # "@companyname.com"

###################################
# ADS Output location
###################################
organization_url = ''             # https://dev.azure.com/org-name
ads_project_name = ''             # "Project-Name"
# Default Azure DevOps Tags (separated by ';' character)
tags = 'migration-tag-1'

###################################
#  Local folder names
###################################
# local filepath var for saving work item attachments
work_item_filepath='work_items'
# local filepathvar for saving log files / json data
logging_filepath='logs'
# local filepath for saving work item json map data
json_maps_filepath='json_maps'

############################
###  RTC Query URLs 
###  These are the query URLs that the migration script will run to migrate and link hierarchy
###  Make sure that the queries are organized by RTC Work Item Type, and seperated by commas
###  If your RTC Work Item Type is missing, add it (all lowercase)
############################
rtc_query_urls = {
    'epic':[
        #"https://rtc.ta.company.com/ccm/web/projects/ABC#action=com.ibm.team.workitem.runSavedQuery&id=_123456789"
    ],
    'feature':[],
    'story':[],
    'aststory':[],
    'enhancementstory':[],
    'defectstory':[],
    'sitstory':[],
    'technicalspike':[],
    "specificationstory":[],
    "assessmentstory":[],
}

############################
###  Map RTC Work Item Type to Azure DevOps Work Item Type
###  By default, work item will map to itself (ex: feature:feature, epic:epic)
###  RTC Work Item Type strings are formatted as all lowercase with no spaces
############################
rtc_ads_type_map={
    'technicalspikestory':'story',
    'sitstory':'story',
    'defectstory':'story',
    'enhancementstory':'story',
    'specificationstory':'story',
    "assessmentstory":"story",
    "aststory":"story",
    "itpstory":"story",
}

# Default RTC properties to include in Work Item Queries
default_rtc_properties=['dc:type', 'rtc_cm:plannedFor']

############################
###  Map RTC Property to Azure DevOps Attributes
###  'common' fields will be included for all work item types as well as the specific work item type
###  If your RTC Work Item Type is missing, add it:
#         
# 'work_item_type':{
# 
#    'rtc_query_property':{
#
#        'path':"/fields/System.ADS_Ticket_Attribute_Path",
#
#        'formatting':[ 
#            'additional_function_to_format_value',
#            'ensure_value_max_255_chars' 
#        ]
#     }
#
# }
# 
############################

# Map each RTC property to an ADS attribute
work_items_property_map={

    'common':{
        # RTC PlannedFor -> ADS Iteration (plannedFor value also used for tags)
        "rtc_cm:plannedFor":{
            'path':"/fields/System.IterationPath",
            'formatting':[ 
                'format_ads_iteration_path' 
            ]
        },

        # ADS Area 
        "rtc_cm:filedAgainst":{
            'path':"/fields/System.AreaPath",
            'formatting':[ 
                'format_ads_area_path' 
            ]
        },

        # Story Point / Work Item Size / Progress
        "rtc_cm:progressTracking":{
            'path':'/fields/Microsoft.VSTS.Scheduling.Effort',
            'formatting':[ 
                'format_ads_size' 
            ]
        },


        # RTC Subject + PlannedFor -> ADS Tags
        "dc:subject":{
            'path':'/fields/System.Tags',
            'formatting':[ 
                'format_ads_tags' 
            ]
        },

        # RTC Title -> ADS Title
        "dc:title":{
            # AWS Work Item Title
            'path':'/fields/title',
            'formatting':[ 
                'format_title',
                'char_limit_255'
            ]
        },

        # RTC Description -> ADS Description
        "dc:description":{
            # ADS Work Item Description
            'path':'/fields/System.Description',
            # Formatting to add header info to ADS description
            'formatting':[ 
                'format_description_header' 
            ]
        },

        # RTC ID
        "dc:identifier":{
            # ADS Work Item
            'path':'/fields/Custom.RTCID'
        },

        # RTC work item owner
        "rtc_cm:ownedBy":{
            # ADS Assigned To field
            'path':"/fields/System.AssignedTo",
            # Format RTC user info for ADS
            'formatting':[ 
                'format_ads_user' 
            ]
        },
        
        # ADS ChangedBy
        "rtc_cm:modifiedBy":{
            'path':"/fields/System.ChangedBy",
            'formatting':[ 
                'format_ads_user' 
            ]
        },

        # ADS State
        "rtc_cm:state":{
            'path':"/fields/System.State",
            'formatting':[ 
                'format_ads_state' 
            ]
        },

        # Targeted Release
        "rtc_cm:targeted_release":{
            'path':"/fields/Philips.Planning.Release",
        },

        # Priority
        "oslc_cm:priority":{
            'path':"/fields/Microsoft.VSTS.Common.Priority",
            'formatting':[ 
                'format_ads_priority' 
            ]
        }
       
    },
    
    'epic':{},

    'feature':{

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

        # Planned for Implemented
        'rtc_cm:plannedFor':{
            'path':"/fields/Custom.PlannedforImplemented",
            'formatting':[ 
                'format_string' 
            ]
        },

        # Planned for Implemented RPM
        #'rtc_cm:Planned.for.at.RPM':{
        #    'path':'/fields/Custom.PlannedforImplementedRPM',
        #    'formatting':[ 
        #        'format_string' 
        #    ]
        #},

        # Planned for Done
        #'rtc_cm:Planned.for.Done.Philips':{
        #    'path':'/fields/Custom.PlannedforDone',
        #    'formatting':[ 
        #        'format_string' 
        #    ]
        #},

        # Planned for Done RPM
        #'rtc_cm:Planned.for.Done.at.RPM.Philips':{
        #    'path':'/fields/Custom.PlannedforDoneRPM',
        #    'formatting':[ 
        #        'format_string' 
        #    ]
        #},
    },

    'story':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    'defectstory':{

        # Story Type
        "dc:type":{
            # ADS attribute path
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                # additional value inputting for ADS
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

        # Defect Type
        "rtc_cm:defect":{
            'path':'/fields/Custom.DefectType'
        },

        # Team Track
        "rtc_cm:TTboolean.philips":{
            'path':'/fields/Custom.TeamTrack'
        },

        

    },
    
    'documentationstory':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

    },
    
    'enhancementstory':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    'specificationstory':{
        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },
    
    'sitstory':{
        # Software
        "rtc_cm:SoftwareAtt":{
            'path':'/fields/Custom.Software',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },

        # Sub-Product 
        'rtc_cm:Sub-productAtt':{
            'path':'/fields/Custom.Subproduct',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # Issues Found
        "rtc_cm:issues_found":{
            'path':'/fields/Custom.IssuesFound',
            'formatting':[ 
                'format_string',
                'format_char_limit' 
            ]
        },

        # Number of New Issues Found
        'rtc_cm:Number_of_New_Issues_Found':{
            'path':'/fields/Custom.NumberofNewIssuesFound',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # System Serial number
        'rtc_cm:SystemSerialNumber':{
            'path':'/fields/Custom.SystemSerialNumber',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # System Test Area
        'rtc_cm:system_test_area':{
            'path':'/fields/Custom.SystemTestArea',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },

        # Cart
        'rtc_cm:cart_type':{
            'path':'/fields/Custom.Cart',
            'formatting':[ 
                'format_string',
                'format_char_limit'  
            ]
        },
    },
    
    'technicalspikestory':{

        # Story Type
        "dc:type":{
            'path':"/fields/Custom.StoryType",
            'formatting':[ 
                'format_ads_story_type' 
            ]
        },

        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    
    },

    'frups':{
        # 12NC
        "rtc_cm:PartNumber12NC":{
            'path':"/fields/Custom.12NC"
        }
    },

    "assessmentstory":{
        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    "aststory":{
        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },

    "itpstory":{
        # MVP
        'rtc_cm:MVP.list':{
            'path':"/fields/Custom.MVP"
        },
    },
}


#############################
# Settings
#############################
# rtcclient query variables
validate_only = False
bypass_rules = True
suppress_notifications = True
ends_with_jazz = False
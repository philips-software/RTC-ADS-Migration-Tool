from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import pprint
import CONFIG
import CREDENTIALS

personal_access_token = CREDENTIALS.personal_access_token
organization_url = CREDENTIALS.organization_url
# Create a connection to the org
credentials = BasicAuthentication('', personal_access_token)
connection = Connection(base_url=organization_url, creds=credentials)

# Get a client (the "core" client provides access to projects, teams, etc)
core_client = connection.clients.get_core_client()
wit_client = connection.clients.get_work_item_tracking_client()
identity_client = connection.clients.get_identity_client()
location_client = connection.clients_v5_0.get_location_client()
graph_client = connection.clients_v5_0.get_graph_client()
work_client = connection.clients.get_work_client()
member_ent_mngmnt_client = connection.clients_v5_0.get_member_entitlement_management_client()
wit_5_1_client = connection.clients_v5_1.get_work_item_tracking_client()


print('AZURE LOGIN COMPLETE')
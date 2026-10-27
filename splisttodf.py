#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/splisttodf.py
import pandas as pd     
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.runtime.auth.client_credential import ClientCredential 
from office365.sharepoint.client_context import ClientContext
from dotenv import load_dotenv
import os

garbage_cols = ['FileSystemObjectType', 'Id', 'ServerRedirectedEmbedUri',
       'ServerRedirectedEmbedUrl', 'ContentTypeId', 
       'OData__ColorTag', 'ComplianceAssetId', 'Reference',
       'ID', 'Modified', 'Created', 'AuthorId', 'EditorId',
       'OData__UIVersionString', 'Attachments', 'GUID']

def splisttodf(list_name, site_url):
    # Load credentials from .env file
    load_dotenv()
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')

    if client_id and client_secret:
        try:
            ctx_auth = AuthenticationContext(site_url)
            if ctx_auth.acquire_token_for_user(client_id, client_secret):
                ctx = ClientContext(site_url, ctx_auth)
                web = ctx.web
                ctx.load(web)
                ctx.execute_query()

                # Access the list
                list_obj = ctx.web.lists.get_by_title(list_name)
                items = list_obj.items
                fields = list_obj.fields

                # Get display names of columns to rename in the dataframe
                ctx.load(fields)
                ctx.execute_query()
                field_mapping = {}
                for field in fields:
                    field_mapping[field.internal_name] = field.title

                field_mapping = {key: item for key, item in field_mapping.items() if 'field' in key or 'Title' in key}

                # Pagination to retrieve all items
                data = []
                paged_items = items.paged()  # Enables pagination
                while True:
                    ctx.load(paged_items)
                    ctx.execute_query()
                    for item in paged_items:
                        data.append(item.properties)
                    if not paged_items.has_next:  # Check if more pages are available
                        break
                    paged_items = paged_items.get_next()

                # Convert data to a pandas DataFrame
                df = pd.DataFrame(data)
                df.rename(columns=field_mapping, inplace=True)
                # Drop Garbage cols
                df = df.drop(columns=garbage_cols, axis=1)

                return df, field_mapping.values()
            else:
                print("Cannot access ARIS database. Authentication failed")
        except ConnectionError as e:
            print(f"Cannot access ARIS database. Please revise your connection. Error: {e}")
            return None, None
        except ValueError as e:
            print(f"Cannot access ARIS database. Please revise your credentials. Error: {e}")
            return None, None
        except Exception as e:
            print(f"Cannot access ARIS database. Exception Error: {e}")
            return None, None
    else:
        print('Cannot access ARIS database. Missing .env file')
        return None, None

if __name__ == '__main__':
    df = splisttodf()
    print(df['Acronym'])
    

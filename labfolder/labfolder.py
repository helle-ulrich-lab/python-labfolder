from getpass import getpass
from requests import (get as GET,
                      post as POST, 
                      delete as DELETE, 
                      patch as PATCH)
from datetime import datetime
from typing import Union

class LabFolderApiException(Exception):

    """A class to handle errors received from the LabFolder API"""

    def __init__(self, message: str = '', error: dict = {}):
        api_message = error.get('message', '')
        message = api_message if api_message else message
        super().__init__(message)

class User(object):

    """A class to represent a LabFolder user"""

    def __init__(self, user_data: dict) -> None:
        self.group_membership_id = user_data.get('id', None) if user_data.get('user', None) else None
        user_data = user_data.get('user', user_data)
        self.id = user_data.get('id', None)
        self.first_name = user_data.get('first_name', None)
        self.last_name = user_data.get('last_name', None)
        self.email = user_data.get('email', None)

        self._headers = dict()
        self._logged_in = False

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name} <{self.email}>'
    
    def __repr__(self) -> str:
        return self.__str__()
    
class Group(object):

    """A class to represent a LabFolder group"""

    def __init__(self, data: dict) -> None:
        self.id = data['id']
        self.name = data['name']
        self.users = [User(u) for u in data['children']]

    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def get_user(self, username: str = '', id=None) -> User:
        """
        Takes a LabFolder username, i.e. an email address, or ID
        and returns the corresponding User from the list of Users that
        make up the Group
        """

        if id:
            return next((u for u in self.users if u.id == str(id)), None)

        if username:
            return next((u for u in self.users if u.email == username), None)

        return None

class BaseRecord(object):

    """
    A base class to define the attributes common to all
    LabFolder objects other than User or Group
    """

    def __init__(self, data: dict) -> None:
        datetime_format = '%Y-%m-%dT%H:%M:%S.%f%z'
        self.id = data.get('id', None)
        self.title = data.get('title', None)
        self.hidden = data.get('hidden', False)
        try:
            self.creation_date = datetime.strptime(data.get('creation_date', None), datetime_format)
        except:
            self.creation_date = None
        try:
            self.version_date = datetime.strptime(data.get('version_date', None), datetime_format)
        except:
            self.version_date = None

    def __str__(self) -> str:
        return f'{self.__class__.__name__} {self.id} - {self.title}'

    def __repr__(self) -> str:
        return self.__str__()

class Folder(BaseRecord):

    """A class to represent a LabFolder folder"""

    def __init__(self, data: dict) -> None:
        super(Folder, self).__init__(data=data)
        self.owner_id = data.get('owner_id', None)
        self.group_id = data.get('group_id', None)
        self.parent_folder_id = data.get('parent_folder_id', None)
        self.folder_id = data.get('folder_id', None)
    
class Entry(BaseRecord):

    """A class to represent a LabFolder entry"""

    def __init__(self, data: dict) -> None:
        super(Entry, self).__init__(data=data)
        self.author_id = data.get('author_id', None)
        self.version_id = data.get('version_id', None)
        self.project_id = data.get('project_id', None)
        self.entry_number = data.get('entry_number', None)
        self.editable = data.get('editable', False)

class Project(BaseRecord):

    """A class to represent a LabFolder project"""

    def __init__(self, data: dict) -> None:
        super(Project, self).__init__(data=data)
        self.owner_id = data.get('owner_id', None)
        self.group_id = data.get('group_id', None)
        self.folder_id = data.get('folder_id', None)

class LabFolder(object):

    def __init__(self):
        self.me = None
        self.group = None
        self._api_base_url = 'https://labfolder.labforward.app/api/v2'
        self._api_num_limit = 20

    def _check_logged_in(self) -> bool:
        """
        Check if me is set, that is a user has
        been logged in.
        """

        if not self.me:
            raise Exception('You are not logged in. '
                            'Please log in before performing this action.')
        
        return True
    
    @staticmethod
    def _check_group_membership(user: User) -> bool:
        """
        Check if user has group membership id.
        """

        if not user.group_membership_id:
            raise Exception('You have not set a group. '
                            'Please set a group before running this function.')

        return True

    def _get_logged_user(self, headers: dict) -> User:
        """Get details of logged user."""

        r = GET(f'{self._api_base_url}/me',
                params={'expand': 'user'},
                headers=headers)

        if r.status_code == 200:
            user_data = r.json()
            user = User(user_data)
            return user
        else:
            raise LabFolderApiException(error=r.json())

    def login(self, username: str) -> None:
        """
        Authenticate a user with LabFolder and generate the token
        necessary to make API calls.
        N.B.: The supplied password is destroyed immediately after obtaining
        the token.
        """

        # Checks
        if self.me:
            raise Exception('You are already logged in. '
                            'Log out before logging in again.')

        # Data to be posted
        password = getpass(prompt='Password: ')
        credentials = {'user': username,
                       'password': password}

        # Send request
        r = POST(f'{self._api_base_url}/auth/login',
                 json=credentials)

        # Erase password
        password = None

        # Evaluate response
        if r.status_code == 200:
            token = r.json()['token']
            headers = {'User-Agent': f'LabFolderApi; {username}',
                       'Authorization': f'Bearer {token}'}
            self.me = self._get_logged_user(headers=headers)
            self.me._headers = headers
            self.me._logged_in = True
            print(f'You are logged in as: {self.me}')
        else:
            raise LabFolderApiException(error=r.json())

    def logout(self) -> None:
        """Reset me and group. Invalidate token."""

        # Checks
        self._check_logged_in()

        # Send request
        r = POST(f'{self._api_base_url}/auth/logout',
                 headers=self.me._headers)

        # Evaluate response
        if r.status_code == 204:
            self.me = None
            self.group = None
            print('Logged out')
        else:
            raise LabFolderApiException(error=r.json())

    def get_group(self, group_id: int) -> Group:
        """Given an ID, get the corresponding group"""

        # Checks
        self._check_logged_in()

        # Send request
        r = GET(f'{self._api_base_url}/groups/{group_id}/tree',
                headers=self.me._headers)

        # Evaluate response
        if r.status_code == 200:
            data = r.json()
            return Group(data)
        else:
            raise LabFolderApiException(error=r.json())

    def set_group(self, group_id: str):
        """
        Given an ID, get the corresponding group and add it to
        the group attribute.
        """

        # Set group
        group = self.get_group(group_id=group_id)
        self.group = group
        print(group)

        # If available, set group_membership_id for me
        me = self.group.get_user(id=self.me.id)
        if me:
            self.me.group_membership_id = me.group_membership_id

    def get_entries_projects(self, user: User = None, limit: int = 0) -> list:
        """
        Get entries and projects for a user.
        Both are returned because, as far as one can see,
        it is not possible to get entries without specifying
        projects.
        If no user is specified, me is used.
        If no limit is specified, all records are returned.
        """

        # Checks
        self._check_logged_in()

        # Set user
        if not user:
            user = self.me

        # Set limits
        max_limit = 0
        if not limit:
            limit = self._api_num_limit
        elif limit > self._api_num_limit:
            max_limit = limit
            limit = self._api_num_limit
        else:
            max_limit = limit
            limit = limit

        # Get projects
        projects = self.get_projects(user=user)
        project_ids = [p.id for p in projects]

        # Get entries
        entries = []
        offset = 0
        
        while True:
            
            # Send request
            r = GET(f'{self._api_base_url}/entries',
                    params={'project_ids': project_ids,
                            'limit': limit,
                            'offset': offset},
                    headers=self.me._headers)

            # Evaluate response
            if r.status_code == 200:

                partial = [Entry(d) for d in r.json()]
                entries.extend(partial)
                offset += limit

                if len(partial) < limit:
                    break

                if max_limit:
                    if len(entries) == max_limit:
                        break
                    if len(entries) + limit > max_limit:
                        limit = max_limit - len(entries)

            else:
                raise LabFolderApiException(error=r.json())

        return entries, projects

    def _get_records(self, rec_obj: Union[Project, Folder], user: User = None, limit:  int = 0) -> list:
        """
        Get projects or folders for a user.
        If no user is specified, me is used.
        If no limit is specified, all records are returned.
        """

        # Checks
        self._check_logged_in()

        # Set user
        if not user:
            user = self.me

        # Set limits
        max_limit = 0
        if not limit:
            limit = self._api_num_limit
        elif limit > self._api_num_limit:
            max_limit = limit
            limit = self._api_num_limit
        else:
            max_limit = limit
            limit = limit

        # Get records
        records = []
        offset = 0
        record_type = f'{rec_obj.__name__.lower()}s'
        
        while True:
            
            # Send request
            r = GET(f'{self._api_base_url}/{record_type}',
                    params={'owner_id': user.id,
                            'limit': limit,
                            'offset': offset},
                    headers=self.me._headers)

            # Evaluate response
            if r.status_code == 200:

                partial = [rec_obj(d) for d in r.json()]
                records.extend(partial)
                offset += limit

                if len(partial) < limit:
                    break

                if max_limit:
                    if len(records) == max_limit:
                        break
                    if len(records) + limit > max_limit:
                        limit = max_limit - len(records)

            else:
                raise LabFolderApiException(error=r.json())

        return records

    def get_folders(self, user: User = None, limit: int = 0) -> list:
        """
        Get folders for a user.
        If no user is specified, me is used.
        If no limit is specified, all records are returned.
        """

        return self._get_records(rec_obj=Folder, user=user, limit=limit)

    def get_projects(self, user: User = None, limit: int = 0) -> list:
        """
        Get projects for a user.
        If no user is specified, me is used.
        If no limit is specified, all records are returned.
        """

        return self._get_records(rec_obj=Project, user=user, limit=limit)

    def set_owner(self, record: Union[Folder, Project], new_owner: User) -> None:
        """Set the owner of a record to a specific user."""

        # Checks
        self._check_logged_in()
        self._check_group_membership(new_owner)

        # Check that record is of the right type
        rec_obj_name = record.__class__.__name__
        if rec_obj_name not in ['Folder', 'Project']:
            raise Exception(f'Setting the owner for "{rec_obj_name}" is not yet suported.')

        # Data to be sent with patch
        data = f'[{{"op":"replace", "path": "/owner_id", "value": "{new_owner.group_membership_id}"}}]'
        patch_headers = {**self.me._headers, **{'Content-Type': 'application/json-patch+json'}}
        record_type = f'{rec_obj_name.lower()}s'

        # Send request
        r = PATCH(f'{self._api_base_url}/{record_type}/{record.id}',
                                data=data,
                                headers=patch_headers)
        
        # Evaluate response
        if r.status_code == 200:
            print(f'Set owner for "{record}" to {new_owner}')
        else:
            raise LabFolderApiException(error=r.json())

    def remove_user_from_group(self, user: User) -> None:
        """Remove a user from a group."""

        # Checks
        self._check_logged_in()
        self._check_group_membership(user)

        # Send request
        r = DELETE(f'{self._api_base_url}/group-memberships/{user.group_membership_id}',
                              headers=self._headers)
        
        # Evaluate response
        if r.status_code == 204:
            print(f'{user} has been removed from {self.group}')
        else:
            raise LabFolderApiException(error=r.json())

    def export_as_pdf(self, record: Union[Entry, Project]) -> None:
        """Export an entry or a project as PDF."""

        # Checks
        self._check_logged_in()
        
        # Check that record is of the right type
        rec_obj_name = record.__class__.__name__
        if rec_obj_name not in ['Entry', 'Project']:
            raise Exception(f'Exporting "{rec_obj_name}" is not yet suported.')

        # Data to be posted
        data = {
            "download_filename": f'{rec_obj_name}_{record.id}',
            "settings": {
                "preserve_entry_layout": True
            },
            "content": {f'{rec_obj_name.lower()}_ids':  [record.id]}
        }

        # Send request
        r = POST(f'{self._api_base_url}/exports/pdf',
                            json=data,
                            headers=self.me._headers)
        
        # Evaluate response
        if r.status_code == 202:
            print(f'Export successful for "{record}". '
                  'Check your account on the web to download the PDF.')
        else:
            raise LabFolderApiException(error=r.json())

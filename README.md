# python-labfolder

This is a basic implementation of the [LabFolder API v2](https://labfolder.labforward.app/api/v2/docs/development.html) in Python.

## Installation

`git clone https://github.com/helle-ulrich-lab/python-labfolder`

With conda

`conda create -n labfolder_api python==3.11 requests # ipykernel, if you want to use the included Jupyter notebook`

## Usage

```python
import labfolder

lf = labfolder.LabFolder()

# Log in
lf.login(username='yourusername@system.com')

# Set a group
lf.set_group(group_id=1234)

# Get users from the group
user1 = lf.group.get_user(username='user1@system.com')
user2 = lf.group.get_user(username='user2@system.com')

# Get folders, entries and projects for a user.
# If no user is provided, it defaults to the
# logged user
folders = lf.get_folders(user=user1)
entries, projects = lf.get_entries_projects(user=user1)

# Change the owner of a folder
lf.set_owner(record=folders[0], new_owner=user2)

# Export an entry as PDF
lf.export_as_pdf(record=entries[0])

# Log out
lf.logout()
```

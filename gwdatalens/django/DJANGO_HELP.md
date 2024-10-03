# GWDataLens under BRO-Connector

In order to run GW DataLens under BRO Connector (a Django application), follow these steps:

1. Modify `gwdatalens/app/config.toml` and set `DJANGO_APP = true`.
2. Copy GW DataLens to BRO-Connector folder. See section below for a command that makes this step very simple.
3. Modify Django files (`main/settings/base.py` and `main/urls.py`) so GW DataLens can be found by the django app.

## Copy GW DataLens to Django Application

Use command line tool `cp_gwdatalens_to_broconnector [PATH]`, providing the
path to the root of the BRO Connector application. Or run script
`gwdatalens/django_copy.py`. Ensure the path to the Django Application is
correctly defined in the script. This copies all relevant files to the right
locations in the Django Application.

## Update urlpatterns

Add the following lines to `main/urls.py`:

```python
from gwdatalens.app import app as gwdatalens_app
from gwdatalens.views import render_gwdatalens_tool

admin.autodiscover()
gwdatalens_app  # noqa

# Add to urlpatterns:
urlpatterns = [
    path("django_plotly_dash/", include("django_plotly_dash.urls")), # maybe already present
    path("gwdatalens/", render_gwdatalens_tool, name="gwdatalens"),
]
```

## Update settings

In `main/settings/base.py`, add all settings listed in
`gwdatalens/django/plotly_settings.py`. In some cases the settings variables
must be added in others, the existing lists must be extended. Be sure to add
additional entries at the bottom of existing lists.

## Prepare Django app

Run the following commands from `bro_connector/` (directory containing `manage.py`):

- `python manage.py makemigrations bro tools gmw gld gmn frd`
- `python manage.py migrate`
- `python manage.py createsuperuser` (pick defaults and choose a password)
- `python manage.py runserver` (this runs the app!)

## Starting from scratch for Django App

### Install postgresql

<https://www.postgresql.org/download/linux/ubuntu/>

```bash
sudo apt install postgresql postgresql-common postgresql-contrib
```

### Install postgis

<https://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS3UbuntuPGSQLApt>

### Install PgAdmin4

<https://www.pgadmin.org/download/pgadmin-4-apt/>

#### Ensure user postgres has a password

Run `sudo -su postgres psql`. In the command line type

```sql
ALTER USER postgres PASSWORD '<password>';
```

#### Connect to server in PgAdmin4

Register server, as host choose localhost. For user choose postgres and enter the password you chose above.

#### Create database

Create database with name `grondwatermeetnet` by right-clicking on Databases and selecting `Create > Database`.

Restore backup from file by right-clicking on database and selecting `Restore...` and selecting SQL file containing backup.

#### Issue with spatial_ref_sys

If gwdatalens is not working because of spatial_ref_sys error

- Export CSV file by right clicking on gisdb > schemas > postgis > tables > spatial_ref_sys
- Select Import/Export Data...
- Choose Export, select a file name, and under Options turn on Header option.
- Press OK.
- Right-click grondwatermeetnet and select PSQL tool
- Enter the following command:

```sql
CREATE TABLE spatial_ref_sys ( 
  srid       INTEGER NOT NULL PRIMARY KEY, 
  auth_name  VARCHAR(256), 
  auth_srid  INTEGER, 
  srtext     VARCHAR(2048), 
  proj4text  VARCHAR(2048) 
)
```

- Refresh the database and right click on grondwatermeetnet > schemas > public > tables > spatial_ref_sys
- Select Import/Export Data...
- Choose Import, and select CSV file we just exported. Under options make sure the Headers option is turned on.
- Press OK.

### Check which column in databse contains observations

If no observations are showing up, check whether the value_column in the `DataSource`
class is correct. Can be one of:

- "field_value"
- "calculated_value"

Set this value in `gwdatalens/app/src/data/source.py`

## Uninstall postgresql

<https://askubuntu.com/questions/32730/how-to-remove-postgres-from-my-installation>

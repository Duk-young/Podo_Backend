# CSE416 PODO BACKEND BY TEAM ONE-EGO

## Database Scheam can be found:
- https://dbdocs.io/amdy1997/CSE416_Data_Schema?view=table_structure

## Backend API Documentation can be found:
- https://app.gitbook.com/s/t2Bs0VKkwGTAaAIr09Ja/reference/api-reference
- Please note that some APIs are for internal use, they are not listed in the API documentation.

## Backend Repo has been deployed via Heroku. You don't have to install the backend in your local!
- https://podo-backend.herokuapp.com/

- you can also install backend in your local computer by following the instructions below.

## Before the installation
### The system requires environment variables to run. This can be found in our team Slack.
- https://join.slack.com/t/cse416voyage/shared_invite/zt-1aekg8yg0-BX9fhsYIVvxDHvDsL7S24w

## Local Backend Installation

- Please follow the instructions below if you pulled back-end repo for the first time.

## Without Docker
### For Windows

```bash
# Create the env
py -3 -m venv venv

# Activate the env
venv\Scripts\activate

# install packages
pip install -r requirements.txt
```

### For Mac

```bash
# Create the env
python3 -m venv venv

# Activate the env
. venv/bin/activate

# install packages
pip3 install -r requirements.txt
```

## Server start

```bash
# Starts backend server in local
python server.py

# OR

python3 server.py

# Either one of the command should work for you.
# Please DM me if it does not work for you.
```

## With Docker

- Please install Docker desktop app first
- Then you can execute the commands below to setup the backend server using docker image

```bash
# create docker image and name it as podo_back (commands are specified in Dockerfile)
docker build -t podo_back .

# delete all the exisitng containers
docker rm `docker ps -a -q`

# Server start docker container run (http://localhost:5001 for local use) 
docker run -d --name podo_back_container -p 5001:8888 -t podo_back

# docker container stop
docker stop podo_back_container
```
## Testing APIs
- Our Backend use Fast API Framework which supports swagger-UI
- Default port for backend is set to 5001, so you can access http://localhost:5001/docs to check and try out all the available APIs.

## Instructions for Deployment
- The workflow has been set to create a Docker image and push it to Heroku. So you do not have to worry about it, since it will be deployed as the codes get pushed to main branch

- Please make sure you update a requirements.txt when you install new packages for Backend
```bash
# update requirements.txt
pip freeze > requirements.txt
```

## Bug Report and Suggestions
- Backend bug reports are being made with using Slack.
- https://join.slack.com/t/cse416voyage/shared_invite/zt-1aekg8yg0-BX9fhsYIVvxDHvDsL7S24w

- Please join the Backend Bug Report channel and report bugs you found!
- They will be fixed very soon. Also, feel free to suggest anything you need.

## Auxiliary programs included in this repo

- /vivino-scraper includes files used for scraping wine information from vivino.
    - This does not require any deployment, you can simply run:
    - 1. collectDetails.py to collect urls for wine detail pages
    - 2. urlScrap.py to iterate through urls collected in step 1.

- /recommendations-update includes files that updates csv files needed for wine recommendation APIs.
    - This is already deployed via Heroku. csv files are updated every midnight.
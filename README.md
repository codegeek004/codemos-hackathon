
# 📸 PhotoSpurge

**PhotoSpurge** is a **Django** + **Celery**-based system designed to manage, migrate, and clean up **Google Photos** across accounts. It automates tasks like **photo transfers, deletions, recoveries, uploads, and trashing** while handling large-scale operations with **Celery workers** and a **Redis broker**.

---

## 🚀 Features

* Migrate Google Photos from one account to another.
* Bulk operations: download, upload, delete, recover, move to trash.
* Task scheduling and retries with **Celery** + **Redis**.
* Notifications and monitoring for task execution.
* Secure authentication with **OAuth 2.0** and **Google Photos Library API**.

---

## 🛠️ Tech Stack

* **Backend:** Django 
* **Task Queue:** Celery
* **Message Broker:** Redis
* **Scheduler:** Celery Beat
* **Database:** MySQL
* **Google Cloud:** OAuth 2.0 + Photos Library API

---

## ⚙️ Setup Guide

### 1. Clone Repository

```bash
git clone [https://github.com/yourusername/photospurge.git](https://github.com/yourusername/photospurge.git)
cd photospurge
````

### 2\. Create Virtual Environment

```bash
python3 -m venv env
source env/bin/activate
```

### 3\. Install Dependencies

```bash
pip install -r requirements.txt
```
### 4\. Setup MySQL database
Enter the command with your mysql password and  create a database 'gmail'
```bash
mysql -u root -p
```
```bash
create database gmail
```
Update the user and password in codegeeks/settings.py with your credentials
```bash
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'gmail',
            'USER': '****',
            'PASSWORD': '****',
            'HOST': 'localhost',
            'PORT': 3306,
        }
    }
```
### 5\. Migrate the database

```bash
python manage.py migrate
```
### 6\. Collect the static files

```bash
python manage.py collectstatic
```
### 🔑 Google Cloud Console Setup (Updated)

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).

2.  Create a new project (or select an existing one).

3.  Enable the following APIs:

      * **Google Photos Library API**
      * **OAuth 2.0 Client ID**
      * **Gmail API**

4.  Configure the **OAuth Consent Screen**:

      * Select `External` if sharing with other users.
      * Fill in app details (name, logo, support email).
      * Add scopes: `../auth/photoslibrary.appendonly`, `../auth/photoslibrary.readonly` 
        and`.../auth/gmail.readonly`


5.  Create **OAuth 2.0 Client ID**:

      * Choose `Web Application`.
      * Add Authorized Redirect URI 1:
        `https://127.0.0.1:8000/accounts/google/login/callback/`
    * Add Authorized Redirect URI 2:
        `https://127.0.0.1:8000/photos/destination/auth/callback/`
    

6.  Download the JSON file, rename it to `credentials_local.json`, and place it in the project's root directory.
Or run the command
```bash
    mv ~/Downloads/credentials_local.json your_project_path
```

7.  Create a .env file
    ```ini
    touch .env
    ```
 8. Add following from google cloud console in .env:

    ```ini
    client_id = your_client_id.apps.googleusercontent.com
    client_secret = GOCX********cdx
    gmail_app_password = abcd abcd abcd abcd
    ```

### ⚡ Running Services

  * **Start Django**
    ```bash
    python manage.py runsslserver
    ```

  * **Start Celery Worker in another tab**
    
    *Note: Make sure each time you start a service your virtual  environment is active.*

    ```bash
    celery -A codegeeks worker --loglevel=info
    ```

Now Access the application at https://127.0.0.1:8000/

Note : Deletion from source account feature is in progress.

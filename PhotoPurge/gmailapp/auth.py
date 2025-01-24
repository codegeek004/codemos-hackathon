from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from google.oauth2.credentials import Credentials
from django.contrib import messages
from .utils import retrieve_credentials_for_user
import requests
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.core.mail import EmailMessage
from google.auth.transport.requests import Request
from datetime import datetime, timezone

# to blacklist the token when user logs out. the logout view is defined below.
def blacklist_token(token):
	# url to revoke the token
	url = 'https://oauth2.googleapis.com/revoke'
	payload = {'token': token}
	headers = {'content-type': 'application/x-www-form-urlencoded'}

	response = requests.post(url, data=payload, headers=headers)
	
	if response.status_code == 200:
		return "Token blacklist successful"
	
	else:
		return "Something went wrong"

# to check the validity of token
def check_token_validity(token):
	# url to get the info of token
	url = f'https://oauth2.googleapis.com/tokeninfo?access_token={token}'
	response = requests.get(url)

	if response.status_code == 200:
		valid=True
	else:
		valid=False
	return valid

# this view works with middleware. If the user is active on the website, it will refresh the token using the last_active field from the gmailapp_customuser table
def refresh_google_token(user_id):
    try:
        creds = retrieve_credentials_for_user(user_id)

        if creds and creds.expiry and creds.refresh_token:
            # Ensure `creds.expiry` is a datetime object
            if isinstance(creds.expiry, str):
                creds.expiry = datetime.strptime(creds.expiry, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)

            # Refresh token only if expired
            if creds.expiry < datetime.now(timezone.utc):
                creds.refresh(Request())

                # Update token in SocialToken model
                social_account = SocialAccount.objects.get(user_id=user_id, provider='google')
                social_token = SocialToken.objects.get(account=social_account)

                social_token.token = creds.token
                social_token.expires_at = creds.expiry
                social_token.save()

                return creds.token
    except Exception as e:
        print('Exception during token refresh:', e)

    return None


def logout_view(request):
	try:
		if request.user.is_authenticated:
			creds = retrieve_credentials_for_user(request.user)
			print('\nmytoken', creds.token)
			blacklist_access_token = blacklist_token(creds.token)
			print(blacklist_access_token)
			if check_token_validity(creds.token) == False:
				request.session.flush()
				logout(request)
				return redirect('index')
			else:
				messages.warning(request, 'Something went wrong')

	except Exception as e:
		print(f"exception{e}")

	return redirect('index')





	





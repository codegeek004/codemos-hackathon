from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib import messages
from .utils import retrieve_credentials_for_user
import requests
from django.contrib.auth import logout
from django.shortcuts import redirect
import datetime
from django.utils.timezone import now, localtime
from django.core.mail import EmailMessage
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
def refresh_google_token(user):
    try:
        social_token = SocialToken.objects.get(account__user=user, account__provider='google')
        if social_token.token_secret:
            refresh_token = social_token.token_secret
            client_id = social_token.app.client_id
            client_secret = social_token.app.secret

            token_url = 'https://oauth2.googleapis.com/token'
            data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            }

            response = requests.post(token_url, data=data)
            if response.status_code == 200:
                new_token_data = response.json()
                social_token.token = new_token_data['access_token']
                expires_in = new_token_data.get('expires_in')
                if expires_in:
                    social_token.expires_at = timezone.now() + timedelta(seconds=expires_in)
                social_token.save()
                return True
            else:
                print("Failed to refresh token:", response.json())
                return False
        else:
            print("No refresh token available.")
            return False
    except SocialToken.DoesNotExist:
        print("Social token not found for user.")
        return False

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





	





from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib import messages
from .utils import retrieve_credentials_for_user
import requests
from django.contrib.auth import logout
from django.shortcuts import redirect

def blacklist_token(token):
	url = 'https://oauth2.googleapis.com/revoke'
	payload = {'token': token}
	print('payload', payload)
	headers = {'content-type': 'application/x-www-form-urlencoded'}
	print('headers', headers)

	response = requests.post(url, data=payload, headers=headers)
	print('response', response)
	print('response text', response.text)
	if response.status_code == 200:
		return "Token blacklist successful"
	else:
		return "Something went wrong"

def check_token_validity(token):
	url = f'https://oauth2.googleapis.com/tokeninfo?access_token={token}'
	response = requests.get(url)

	if response.status_code == 200:
		valid=True
	else:
		valid=False
	return valid
def refresh_google_token(user):
	print('inside refresh google access token')
	try:
		social_token = SocialToken.objects.get(account__user=user, account__provider='google')
		refresh_token = social_token.token_secret

		social_app = SocialApp.objects.get(provider='google')
		client_id = social_app.client_id
		client_secret = social_app.secret

		url = "https://oauth2.googleapis.com/token"
		data = {
			"client_id": client_id,
			"client_secret": client_secret,
			"refresh_token": refresh_token,
			"grant_type": "refresh_token"
		}
		response = requests.post(url, data=data)

		if response.status_code == 200:
			print('token successfully refreshed')
			new_token = response.json()
			social_token.token = new_token['access_token']
			social_token.expires_at = new_token.get('expires_in')  # Update expiry time
			social_token.save()
			return True
		else:
			print("Failed to refresh token:", response.json())
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





	





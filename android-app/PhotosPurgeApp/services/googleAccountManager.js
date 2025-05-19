import {NativeModules} from 'react-native';
const {PhotosAuthModule} = NativeModules;

export const getGoogleAccounts = async () => {
  return await PhotosAuthModule.getAccounts();
};

export const getAuthToken = async email => {
  return await PhotosAuthModule.getToken(email);
};

// services/photoTransfer.js
export const migratePhotos = async token => {
  const res = await fetch('https://photosdata-pa.googleapis.com/some-endpoint', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'X-Goog-AuthUser': '0',
      'User-Agent': 'Android-Google-Photos/6.43.0',
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: 'payload_here_based_on_analysis',
  });
  if (!res.ok) throw new Error('Failed to migrate photos');
  return await res.json();
};

export const fetchPhotosFromSender = async (token, email) => {
  const endpoint = 'https://photosdata-pa.googleapis.com/YOUR_DYNAMIC_PATH'; // update this based on logs
  const payload = `email=${email}`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-Goog-AuthUser': '0',
      'User-Agent': 'Android-Google-Photos/6.43.0',
    },
    body: payload,
  });

  const text = await response.text();
  console.log('Photo Fetch Response:', text);
  // TODO: parse and extract real photo tokens here
  return [
    { id: 'photo1', token: 'EXTRACTED_TOKEN_1' },
    { id: 'photo2', token: 'EXTRACTED_TOKEN_2' },
  ];
};

export const transferPhotoToSharedArea = async (photo, token, email) => {
  const endpoint = 'https://photosdata-pa.googleapis.com/YOUR_OTHER_DYNAMIC_PATH'; // update this
  const payload = `photo_token=${photo.token}&email=${email}`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-Goog-AuthUser': '0',
      'User-Agent': 'Android-Google-Photos/6.43.0',
    },
    body: payload,
  });

  const text = await response.text();
  console.log('Transfer Response:', text);
  return text;
};


import React from 'react';
import { Button, Alert } from 'react-native';

export default function TransferButton({ token, email }) {
  const handleFetchPhotos = async () => {
    try {
      const response = await fetch('https://photoslibrary.googleapis.com/v1/mediaItems', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const json = await response.json();
      console.log(json);
      Alert.alert('Photos fetched', `Fetched ${json.mediaItems?.length || 0} photos`);
    } catch (err) {
      console.error(err);
      Alert.alert('Error', 'Failed to fetch photos');
    }
  };

  return <Button title="Transfer Photos" onPress={handleFetchPhotos} />;
}

import React, { useState } from 'react';
import { View, Button, Text, TextInput, ScrollView } from 'react-native';
import RNFS from 'react-native-fs';
import axios from 'axios';

export default function App() {
  const [photoUrls, setPhotoUrls] = useState('');
  const [status, setStatus] = useState('');
  const [sourceCookie, setSourceCookie] = useState('');
  const [destCookie, setDestCookie] = useState('');
  const [userAgent, setUserAgent] = useState('');

  const migratePhotos = async () => {
    setStatus('Starting migration...');
    const urls = photoUrls.split('\n').map(u => u.trim()).filter(Boolean);
    for (const [index, url] of urls.entries()) {
      try {
        setStatus(`Downloading photo ${index + 1}...`);
        const photoData = await axios.get(url, {
          responseType: 'arraybuffer',
          headers: {
            'Cookie': sourceCookie,
            'User-Agent': userAgent,
          },
        });

        const filePath = `${RNFS.DocumentDirectoryPath}/photo${index}.jpg`;
        await RNFS.writeFile(filePath, Buffer.from(photoData.data), 'base64');

        setStatus(`Uploading photo ${index + 1}...`);
        const uploadResp = await axios.post(
          'https://photos.google.com/data/photoUpload', // Replace this with actual upload endpoint from captured traffic
          photoData.data,
          {
            headers: {
              'Content-Type': 'image/jpeg',
              'Cookie': destCookie,
              'User-Agent': userAgent,
              // Add other necessary headers you find in Android upload traffic
            },
          }
        );

        setStatus(`Uploaded photo ${index + 1}`);
      } catch (err) {
        console.error(err);
        setStatus(`Failed on photo ${index + 1}: ${err.message}`);
      }
    }
    setStatus('Migration complete!');
  };

  return (
    <ScrollView style={{ padding: 20 }}>
      <Text style={{ marginBottom: 5 }}>Source Account Cookie:</Text>
      <TextInput
        value={sourceCookie}
        onChangeText={setSourceCookie}
        multiline
        style={{ borderWidth: 1, marginBottom: 10, padding: 5 }}
      />

      <Text style={{ marginBottom: 5 }}>Destination Account Cookie:</Text>
      <TextInput
        value={destCookie}
        onChangeText={setDestCookie}
        multiline
        style={{ borderWidth: 1, marginBottom: 10, padding: 5 }}
      />

      <Text style={{ marginBottom: 5 }}>User-Agent:</Text>
      <TextInput
        value={userAgent}
        onChangeText={setUserAgent}
        style={{ borderWidth: 1, marginBottom: 10, padding: 5 }}
      />

      <Text style={{ marginBottom: 5 }}>Photo URLs (one per line):</Text>
      <TextInput
        value={photoUrls}
        onChangeText={setPhotoUrls}
        multiline
        style={{ borderWidth: 1, marginBottom: 20, padding: 5, height: 100 }}
      />

      <Button title="Migrate Photos" onPress={migratePhotos} />
      <Text style={{ marginTop: 20 }}>{status}</Text>
    </ScrollView>
  );
}


import React, { useRef, useState } from 'react';
import { View, Button, Text, StyleSheet, ActivityIndicator, ScrollView, Alert } from 'react-native';
import { WebView } from 'react-native-webview';
import CryptoJS from 'crypto-js';

const GOOGLE_PHOTOS_URL = 'https://photos.google.com/';

export default function App() {
  const webViewRef = useRef(null);
  const [step, setStep] = useState<'source' | 'destination' | 'done'>('source');
  const [showWebView, setShowWebView] = useState(true);
  const [sourceCookies, setSourceCookies] = useState('');
  const [destinationCookies, setDestinationCookies] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');

  const injectJS = `
    setTimeout(() => {
      window.ReactNativeWebView.postMessage(document.cookie);
    }, 3000);
    true;
  `;

  const handleMessage = (event: any) => {
    const cookie = event.nativeEvent.data;

    if (step === 'source') {
      setSourceCookies(cookie);
      setStatus('✅ Source cookies extracted');
      setStep('destination');
      setShowWebView(true); // open destination login
    } else if (step === 'destination') {
      setDestinationCookies(cookie);
      setStatus('✅ Destination cookies extracted');
      setStep('done');
      setShowWebView(false);
    }
  };

  const extractSAPISIDHASH = (cookie: string) => {
    const sapisidMatch = cookie.match(/SAPISID=([^;]+)/);
    if (!sapisidMatch) return '';
    const sapisid = sapisidMatch[1];
    const origin = 'https://photos.google.com';
    const time = Math.floor(new Date().getTime() / 1000);
    const input = `${time} ${sapisid} ${origin}`;
    const hash = CryptoJS.SHA1(input).toString();
    return `SAPISIDHASH ${time}_${hash}`;
  };

  const migratePhotos = async () => {
    setLoading(true);
    setStatus('⏳ Migrating photos...');

    try {
      const authHeaderSource = extractSAPISIDHASH(sourceCookies);
      const authHeaderDest = extractSAPISIDHASH(destinationCookies);

      const headersSource = {
        'Authorization': authHeaderSource,
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-Same-Domain': '1',
        'X-Goog-AuthUser': '0',
        'Cookie': sourceCookies,
      };

      const headersDest = {
        'Authorization': authHeaderDest,
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-Same-Domain': '1',
        'X-Goog-AuthUser': '0',
        'Cookie': destinationCookies,
      };

      const batchUrl = 'https://photos.google.com/_/PhotosUi/data/batchexecute';

      // 1. Get list of photo tokens from source
      //const photoListBody = `f.req=${encodeURIComponent(JSON.stringify([["af.afp", JSON.stringify({albumId: null, pageSize: 50})]]) + '&'])}`;
      const photoListBody = `f.req=${encodeURIComponent(JSON.stringify([["af.afp", JSON.stringify({albumId: null, pageSize: 50})]]))}&`;

      const photoListResp = await fetch(batchUrl, {
        method: 'POST',
        headers: headersSource,
        body: photoListBody,
      });
      const photoListText = await photoListResp.text();
      const photoTokens = extractPhotoTokensFromResponse(photoListText); // You’ll define this below

      if (!photoTokens.length) throw new Error('No photo tokens found');

      // 2. Upload to destination
      //const addPhotosBody = `f.req=${encodeURIComponent(JSON.stringify([["af.apf", JSON.stringify({photoTokens, albumId: null})]]) + '&'])}`;
      const addPhotosBody = `f.req=${encodeURIComponent(JSON.stringify([["af.apf", JSON.stringify({photoTokens, albumId: null})]]))}&`;

      await fetch(batchUrl, {
        method: 'POST',
        headers: headersDest,
        body: addPhotosBody,
      });

      setStatus(`✅ Migrated ${photoTokens.length} photos successfully`);
    } catch (err: any) {
      setStatus('❌ Migration failed: ' + err.message);
      Alert.alert('Error', err.message);
    } finally {
      setLoading(false);
    }
  };

  const extractPhotoTokensFromResponse = (response: string) => {
    try {
      const match = response.match(/\[\["af\.afp",(.*?)\]\]/);
      if (!match) return [];
      const json = JSON.parse(match[1]);
      const items = json[1][1];
      return items.map((item: any) => item[0]); // each [token, ...]
    } catch {
      return [];
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>📷 Google Photos Migrator</Text>

      {status && <Text style={styles.status}>{status}</Text>}

      {showWebView && (
        <View style={{ height: 500, width: '100%', marginBottom: 10 }}>
          <WebView
            ref={webViewRef}
            source={{ uri: GOOGLE_PHOTOS_URL }}
            javaScriptEnabled={true}
            injectedJavaScript={injectJS}
            onMessage={handleMessage}
            incognito={true}
          />
        </View>
      )}

      {!showWebView && step === 'destination' && (
        <Button title="Login to Destination Account" onPress={() => setShowWebView(true)} />
      )}

      {step === 'done' && !loading && (
        <Button title="🚀 Migrate All Photos" onPress={migratePhotos} />
      )}

      {loading && <ActivityIndicator size="large" color="#007AFF" />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingTop: 60,
    alignItems: 'center',
    backgroundColor: '#fff',
    flexGrow: 1,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  status: {
    marginVertical: 10,
    fontSize: 16,
    color: '#333',
    textAlign: 'center',
  },
});


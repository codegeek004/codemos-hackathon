import React, { useRef, useState } from 'react';
import { View, Text, Button, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { WebView } from 'react-native-webview';
import * as CryptoJS from 'crypto-js';

const GOOGLE_PHOTOS_URL = 'https://photos.google.com';

export default function App() {
  const webViewRef = useRef(null);

  const [currentStep, setCurrentStep] = useState('Idle');
  const [logs, setLogs] = useState<string[]>([]);
  const [sourceCookies, setSourceCookies] = useState<string | null>(null);
  const [destCookies, setDestCookies] = useState<string | null>(null);
  const [sourceEmail, setSourceEmail] = useState('');
  const [destEmail, setDestEmail] = useState('');
  const [webVisible, setWebVisible] = useState(true);
  const [mode, setMode] = useState<'source' | 'dest' | null>(null);

  const log = (msg: string) => {
    console.log(msg);
    setLogs(prev => [...prev, msg]);
  };

  const extractSAPISIDHASH = (cookie: string) => {
    const sapisid = /SAPISID=(.*?);/.exec(cookie)?.[1];
    const origin = 'https://photos.google.com';
    const timestamp = Math.floor(Date.now() / 1000);
    const input = `${timestamp} ${sapisid} ${origin}`;
    const hash = CryptoJS.SHA1(input).toString();
    return `${timestamp}_${hash}`;
  };

  const injectScript = `
    setTimeout(() => {
      window.ReactNativeWebView.postMessage(document.cookie);
    }, 3000);
    true;
  `;

  const extractEmail = async (cookie: string) => {
    const headers = {
      'Authorization': `SAPISIDHASH ${extractSAPISIDHASH(cookie)}`,
      'X-Origin': 'https://photos.google.com',
      'X-Goog-AuthUser': '0'
    };
    const resp = await fetch('https://photos.google.com/_/PeopleDataService/GetPeopleData', {
      method: 'POST',
      headers
    });
    const text = await resp.text();
    const match = text.match(/"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+)"/);
    return match?.[1] || 'Unknown';
  };

  const onMessage = async (event: any) => {
    const cookie = event.nativeEvent.data;
    if (mode === 'source') {
      setSourceCookies(cookie);
      const email = await extractEmail(cookie);
      setSourceEmail(email);
      log(`✅ Source account: ${email}`);
    } else if (mode === 'dest') {
      setDestCookies(cookie);
      const email = await extractEmail(cookie);
      setDestEmail(email);
      log(`✅ Destination account: ${email}`);
    }
    setWebVisible(false);
    setCurrentStep('Idle');
  };

  const fetchPhotos = async (cookie: string) => {
    log('📸 Fetching photo tokens from source account...');
    const sapisidhash = extractSAPISIDHASH(cookie);
    const headers = {
      'Authorization': `SAPISIDHASH ${sapisidhash}`,
      'X-Origin': 'https://photos.google.com',
      'X-Goog-AuthUser': '0',
      'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    };

    const allTokens: string[] = [];
    let nextPageToken = null;

    for (let i = 0; i < 100; i++) {
      const body = `f.req=${encodeURIComponent(JSON.stringify([
        ["af.afp", JSON.stringify({
          albumId: null,
          pageSize: 100,
          pageToken: nextPageToken
        })]
      ]))}&`;

      const response = await fetch('https://photos.google.com/_/PhotosUi/data/batchexecute', {
        method: 'POST',
        headers,
        body,
      });

      const text = await response.text();
      const jsonData = JSON.parse(text.split('\n')[3])[2];
      const innerData = JSON.parse(jsonData);

      const items = innerData[1] || [];
      const tokens = items.map((item: any) => item[0]);
      allTokens.push(...tokens);

      nextPageToken = innerData[3];
      if (!nextPageToken) break;
    }

    log(`✅ Total photos fetched: ${allTokens.length}`);
    return allTokens;
  };

  const migratePhotos = async () => {
    if (!sourceCookies || !destCookies) {
      log('❌ Please extract cookies for both accounts.');
      return;
    }

    setCurrentStep('Migrating...');
    const photoTokens = await fetchPhotos(sourceCookies);

    if (photoTokens.length === 0) {
      log('❌ No photos found to migrate.');
      return;
    }

    log('🔁 Starting photo migration...');
    const sapisidhash = extractSAPISIDHASH(destCookies);
    const headers = {
      'Authorization': `SAPISIDHASH ${sapisidhash}`,
      'X-Origin': 'https://photos.google.com',
      'X-Goog-AuthUser': '0',
      'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    };

    const body = `f.req=${encodeURIComponent(JSON.stringify([
      ["af.apf", JSON.stringify({
        albumId: null,
        photoTokens,
      })]
    ]))}&`;

    const response = await fetch('https://photos.google.com/_/PhotosUi/data/batchexecute', {
      method: 'POST',
      headers,
      body,
    });

    const success = response.ok;
    if (success) {
      log('✅ Photos migrated successfully!');
    } else {
      log('❌ Migration failed.');
    }

    setCurrentStep('Done');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>📷 Google Photos Migrator</Text>

      <Button title="Login as Source Account" onPress={() => {
        setMode('source');
        setWebVisible(true);
        setCurrentStep('Logging in source...');
      }} />

      <Button title="Login as Destination Account" onPress={() => {
        setMode('dest');
        setWebVisible(true);
        setCurrentStep('Logging in destination...');
      }} />

      <Button title="🚀 Migrate All Photos" onPress={migratePhotos} />

      <ScrollView style={styles.logs}>
        {logs.map((logMsg, i) => (
          <Text key={i} style={styles.log}>{logMsg}</Text>
        ))}
      </ScrollView>

      {webVisible && (
        <WebView
          ref={webViewRef}
          source={{ uri: GOOGLE_PHOTOS_URL }}
          injectedJavaScript={injectScript}
          onMessage={onMessage}
          javaScriptEnabled
          domStorageEnabled
        />
      )}

      {currentStep !== 'Idle' && (
        <ActivityIndicator size="large" color="blue" />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 50, paddingHorizontal: 10 },
  heading: { fontSize: 20, fontWeight: 'bold', marginBottom: 10 },
  logs: { marginTop: 20 },
  log: { fontSize: 14, marginBottom: 5 }
});

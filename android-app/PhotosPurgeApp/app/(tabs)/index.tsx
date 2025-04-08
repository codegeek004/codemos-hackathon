import React, { useState, useRef } from 'react';
import { View, Text, Button, TextInput, ScrollView, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';
import * as Crypto from 'expo-crypto';


export default function App() {
  const [cookieString, setCookieString] = useState('');
  const [destinationEmail, setDestinationEmail] = useState('');
  const [logs, setLogs] = useState<string[]>([]);
  const webviewRef = useRef(null);

  const appendLog = (message: string) => {
    console.log(message);
    setLogs(prev => [...prev, message]);
  };

  const generateSAPISIDHASH = (cookies: string, origin: string) => {
    const sapisidMatch = cookies.match(/SAPISID=([^\s;]+)/);
    if (!sapisidMatch) return '';
    const sapisid = sapisidMatch[1];
    const timestamp = Math.floor(Date.now() / 1000);
    const input = `${timestamp} ${sapisid} ${origin}`;
    return `${timestamp}_${Crypto.CryptoDigestAlgorithm.SHA1}` + Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA1,
      input,
      { encoding: Crypto.CryptoEncoding.HEX }
    ).then(hash => `${timestamp}_${hash}`);
  };

  const handleWebViewMessage = (event: any) => {
    const { data } = event.nativeEvent;
    if (data.startsWith('COOKIE:')) {
      const rawCookies = data.replace('COOKIE:', '');
      setCookieString(rawCookies);
      appendLog('🍪 Cookie string: ' + rawCookies);
      appendLog('✅ Cookies extracted');
    }
  };

  const injectedJS = `
    setTimeout(() => {
      window.ReactNativeWebView.postMessage("COOKIE:" + document.cookie);
    }, 3000);
    true;
  `;

  const fetchPhotoTokens = async () => {
    appendLog('🚀 Starting photo migration...');
    appendLog('🔄 Fetching photo tokens...');

    const origin = 'https://photos.google.com';
    const sapisidHash = await generateSAPISIDHASH(cookieString, origin);

    const fetchWithXsrf = async (xsrfOverride?: string): Promise<string[] | null> => {
      const headers = {
        'Authorization': `SAPISIDHASH ${sapisidHash}`,
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-Same-Domain': '1',
        'X-Goog-AuthUser': '0',
        'X-Goog-Encode-Response-If-Executable': 'base64',
        'X-XSRF-Token': xsrfOverride || '',
        'Cookie': cookieString,
      };

      // const body = `f.req=${encodeURIComponent(JSON.stringify([
      //   [["af.httprm", JSON.stringify({ "photoRequestType": 1, "pageSize": 100 })]
      // ]))}&`;
      const body = `f.req=${encodeURIComponent(JSON.stringify([
  [["af.httprm", JSON.stringify({ "photoRequestType": 1, "pageSize": 20 })]]
]))}&`;

      try {
        const res = await fetch('https://photos.google.com/_/PhotosUi/data/batchexecute?rpcids=af.httprm&source=photosui', {
          method: 'POST',
          headers,
          body,
        });

        const raw = await res.text();
        appendLog('📥 Raw response:\n' + raw);

        const match = raw.match(/\n(\[.+\])/s);
        if (!match) {
          appendLog('❌ Failed to parse batchexecute response');
          return null;
        }

        const payload = JSON.parse(match[1]);

        const xsrf = payload?.[0]?.[10]?.[0]?.[1];
        if (xsrf && !xsrfOverride) {
          appendLog(`🔐 Retrying with extracted XSRF: ${xsrf}`);
          return fetchWithXsrf(xsrf);
        }

        // 🧠 You can parse actual photo tokens here from the payload
        const tokens: string[] = []; // Placeholder

        appendLog(`✅ Fetched ${tokens.length} photo tokens`);
        return tokens;
      } catch (err) {
        appendLog(`❌ Error: ${err}`);
        return null;
      }
    };

    const tokens = await fetchWithXsrf();

    if (!tokens || tokens.length === 0) {
      appendLog('⚠️ No photos found to migrate.');
      return;
    }

    appendLog(`📤 Migrating to ${destinationEmail}...`);
    tokens.forEach((t, i) => appendLog(`➡️ Token ${i + 1}: ${t}`));
    appendLog('✅ Migration complete!');
  };

  return (
    <View style={{ flex: 1, paddingTop: 50 }}>
      {cookieString ? (
        <>
          <TextInput
            style={styles.input}
            placeholder="Enter destination email"
            value={destinationEmail}
            onChangeText={setDestinationEmail}
          />
          <Button title="Migrate All" onPress={fetchPhotoTokens} />
          <ScrollView style={styles.logBox}>
            {logs.map((log, idx) => (
              <Text key={idx} style={styles.logText}>{log}</Text>
            ))}
          </ScrollView>
        </>
      ) : (
        <WebView
          ref={webviewRef}
          source={{ uri: 'https://accounts.google.com/AccountChooser?continue=https://photos.google.com' }}
          injectedJavaScript={injectedJS}
          onMessage={handleWebViewMessage}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  input: {
    padding: 10,
    margin: 10,
    borderColor: '#999',
    borderWidth: 1,
    borderRadius: 4,
  },
  logBox: {
    padding: 10,
    marginTop: 10,
    height: 300,
  },
  logText: {
    fontSize: 12,
    color: '#333',
    marginBottom: 4,
  },
});

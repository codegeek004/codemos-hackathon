import React, { useRef, useState } from 'react';
import { View, Button, Alert, TextInput, Modal, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';
import CryptoJS from 'crypto-js';

export default function PhotosPurgeApp() {
  const webviewRef = useRef(null);
  const [webviewVisible, setWebviewVisible] = useState(false);
  const [destinationModal, setDestinationModal] = useState(false);
  const [destinationEmail, setDestinationEmail] = useState('');
  const [cookies, setCookies] = useState(null);
  const [xsrfToken, setXsrfToken] = useState(null);

  const handleMessage = (event) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'cookies') {
        setCookies(data.cookies);
        Alert.alert('Step 1: Source Login ✅', 'Cookies captured');
        setWebviewVisible(false);
      } else if (data.type === 'xsrf') {
        setXsrfToken(data.xsrfToken);
        Alert.alert('Step 2: XSRF Token ✅', data.xsrfToken || 'Token not found');
      }
    } catch (err) {
      console.error('[ERROR ❌]', err);
      Alert.alert('Error', err.message);
    }
  };

  const extractCookieValue = (cookieStr, key) => {
    const match = cookieStr.match(new RegExp(`${key}=([^;]+)`));
    return match ? match[1] : null;
  };

  const getSAPISIDHASHHeader = (origin, sapisid) => {
    const ts = Math.floor(Date.now() / 1000);
    const input = `${ts} ${sapisid} ${origin}`;
    const hash = CryptoJS.SHA1(input).toString();
    return `SAPISIDHASH ${ts}_${hash}`;
  };

  const fetchPhotos = async () => {
    if (!cookies || !xsrfToken) {
      Alert.alert('Error', 'Login and token required');
      return;
    }

    const sapisid = extractCookieValue(cookies, 'SAPISID');
    const origin = 'https://photos.google.com';
    const authHeader = getSAPISIDHASHHeader(origin, sapisid);

    const batchexecuteUrl = 'https://photos.google.com/_/PhotosUi/data/batchexecute?rpcids=j5ZmUe&source=photos&hl=en&authuser=0';
    const payload = JSON.stringify([
      [
        "j5ZmUe",
        "[null,null,[100,null,null,null],[]]",
        null,
        "generic"
      ]
    ]);

    const response = await fetch(batchexecuteUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'X-Same-Domain': '1',
        'X-Goog-AuthUser': '0',
        'X-Requested-With': 'XMLHttpRequest',
        'X-SAPISID-AUTH': authHeader,
        'X-CSRF-Token': xsrfToken,
        'Origin': origin,
        'Referer': origin + '/',
      },
      credentials: 'include',
      body: `f.req=${encodeURIComponent(payload)}&at=${xsrfToken}`,
    });

    const text = await response.text();
    console.log('[DEBUG] 📦 batchexecute response:', text.slice(0, 1000));
    Alert.alert('Photos fetched ✅', 'Check console for response');
  };

  const injectedJavaScript = `
    (function() {
      let cookiesSent = false;

      function extractAndSend() {
        try {
          if (!cookiesSent) {
            const cookies = document.cookie;
            window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'cookies', cookies }));
            cookiesSent = true;
          }

          let xsrfToken = null;

          if (window._F_ && window._F_.EXTRA && window._F_.EXTRA.XSRF_TOKEN) {
            xsrfToken = window._F_.EXTRA.XSRF_TOKEN;
          }

          if (!xsrfToken) {
            const scripts = document.getElementsByTagName('script');
            for (let i = 0; i < scripts.length; i++) {
              const content = scripts[i].innerText;
              if (content.includes('XSRF_TOKEN')) {
                const match = content.match(/"XSRF_TOKEN":"(.*?)"/);
                if (match) {
                  xsrfToken = match[1];
                  break;
                }
              }
            }
          }

          window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'xsrf', xsrfToken: xsrfToken || null }));
        } catch (e) {
          window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'error', error: e.message }));
        }
      }

      if (document.readyState === 'complete') {
        setTimeout(extractAndSend, 3000);
      } else {
        window.addEventListener('load', () => setTimeout(extractAndSend, 3000));
      }
    })();
  `;

  return (
    <View style={{ flex: 1, justifyContent: 'center', padding: 20 }}>
      <Button title="Login to Source" onPress={() => setWebviewVisible(true)} />
      <View style={{ height: 20 }} />
      <Button title="Enter Destination" onPress={() => setDestinationModal(true)} />
      <View style={{ height: 20 }} />
      <Button title="Migrate All Photos" onPress={fetchPhotos} />

      {/* Hidden WebView */}
      {webviewVisible && (
        <Modal visible transparent>
          <WebView
            ref={webviewRef}
            source={{ uri: 'https://photos.google.com' }}
            javaScriptEnabled
            domStorageEnabled
            injectedJavaScript={injectedJavaScript}
            onMessage={handleMessage}
            onLoadEnd={() => Alert.alert('WebView Loaded ✅')}
          />
        </Modal>
      )}

      {/* Destination Email Modal */}
      <Modal visible={destinationModal} transparent>
        <View style={styles.modalContainer}>
          <View style={styles.modalBox}>
            <TextInput
              placeholder="Enter destination email"
              style={styles.input}
              value={destinationEmail}
              onChangeText={setDestinationEmail}
            />
            <Button title="Save" onPress={() => {
              setDestinationModal(false);
              Alert.alert('Destination Email Set', destinationEmail);
            }} />
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalBox: {
    width: '80%', padding: 20, backgroundColor: 'white', borderRadius: 10,
  },
  input: {
    borderBottomWidth: 1, marginBottom: 10, padding: 5,
  },
});

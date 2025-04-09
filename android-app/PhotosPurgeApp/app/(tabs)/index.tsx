import React, { useRef, useState } from 'react';
// import { View, Text, Button, TextInput, ScrollView, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { View, Text, Button, TextInput, ScrollView, StyleSheet, ActivityIndicator, Alert, FlatList } from 'react-native';

import { WebView } from 'react-native-webview';
import sha1 from 'js-sha1';

type LogType = 'info' | 'success' | 'error' | 'debug' | 'warning';
type MigrationLog = {
  type: LogType;
  message: string;
  timestamp: Date;
  details?: any;
};

const App = () => {
  // Refs and State
  const webviewRef = useRef<WebView>(null);
  const [cookies, setCookies] = useState('');
  const [xsrfToken, setXsrfToken] = useState('');
  const [destinationEmail, setDestinationEmail] = useState('');
  const [logs, setLogs] = useState<MigrationLog[]>([]);
  const [isMigrating, setIsMigrating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchedPhotos, setFetchedPhotos] = useState<any[]>([]);

  // Enhanced logging with color coding
  const addLog = (type: LogType, message: string, details?: any) => {
    const newLog = {
      type,
      message,
      timestamp: new Date(),
      details
    };
    console.log(`[${type.toUpperCase()}] ${message}`, details || '');
    setLogs(prev => [newLog, ...prev].slice(0, 100)); // Keep last 100 logs
  };

  // Extract the REAL CSRF token (__Secure-1PSIDTS)
  const extractSecurityTokens = (cookieHeader: string) => {
    try {
      const psidts = cookieHeader.match(/__Secure-1PSIDTS=([^;]+)/)?.[1];
      const sapisid = cookieHeader.match(/SAPISID=([^;]+)/)?.[1];
      
      addLog('debug', 'Extracted security tokens', {
        hasPSIDTS: !!psidts,
        hasSAPISID: !!sapisid
      });

      return { psidts, sapisid };
    } catch (error) {
      addLog('error', 'Failed to extract security tokens', error);
      return { psidts: '', sapisid: '' };
    }
  };

  // Generate SAPISIDHASH for authentication
  const generateSapisidHash = (sapisid: string) => {
    if (!sapisid) {
      addLog('error', 'Cannot generate SAPISIDHASH - missing SAPISID');
      return '';
    }
    const timestamp = Math.floor(Date.now() / 1000);
    const hash = sha1(`${timestamp} ${sapisid} https://photos.google.com`);
    return `SAPISIDHASH ${timestamp}_${hash}`;
  };

  // Handle WebView messages
  const handleWebViewMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      addLog('debug', 'WebView message received', { type: data.type });

      if (data.type === 'cookies') {
        setCookies(data.cookies);
        const { psidts } = extractSecurityTokens(data.cookies);
        
        if (psidts) {
          setXsrfToken(psidts);
          addLog('success', 'XSRF token (__Secure-1PSIDTS) set successfully');
        } else {
          addLog('error', 'Failed to extract XSRF token from cookies');
        }
      }
    } catch (error) {
      addLog('error', 'WebView message processing failed', error);
    }
  };

  // Make authenticated API request
  const makeApiRequest = async (endpoint: string, rpcids: string, payload: any) => {
    const { psidts, sapisid } = extractSecurityTokens(cookies);
    
    if (!psidts) {
      throw new Error('XSRF token (__Secure-1PSIDTS) missing');
    }

    const headers = {
      'Authorization': generateSapisidHash(sapisid),
      'Content-Type': 'application/x-www-form-urlencoded',
      'Cookie': cookies,
      'X-XSRF-TOKEN': psidts,
      'X-Goog-AuthUser': '0'
    };

    const fullPayload = {
      ...payload,
      rpcids,
      at: 'token_from_initial_load' // Still required but not CSRF
    };

    addLog('debug', 'Making API request', {
      endpoint,
      headers: { ...headers, Authorization: 'REDACTED' },
      payload: { ...fullPayload, 'f.req': 'REDACTED' }
    });

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: new URLSearchParams(fullPayload as any),
    });

    const responseText = await response.text();
    addLog('debug', 'API response received', {
      status: response.status,
      responseLength: responseText.length
    });

    return responseText;
  };

  // Fetch photos with proper CSRF protection
  const fetchPhotos = async () => {
    setIsLoading(true);
    addLog('info', 'Starting photo fetch');
    
    try {
      const response = await makeApiRequest(
        'https://photos.google.com/_/PhotosUi/data/batchexecute',
        'snAcKc,wQ6iqd',
        {
          'f.req': JSON.stringify([/* Your payload here */])
        }
      );

      // Parse response (simplified example)
      const photoUrls = response.match(/https:\/\/photos\.google\.com\/photo\/([a-zA-Z0-9_-]+)/g) || [];
      setFetchedPhotos(photoUrls);
      addLog('success', `Found ${photoUrls.length} photos`);

    } catch (error) {
      addLog('error', 'Photo fetch failed', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Render log items with color coding
  const renderLogItem = ({ item }: { item: MigrationLog }) => {
    const colors = {
      info: '#1976d2',
      success: '#388e3c',
      error: '#d32f2f',
      warning: '#ffa000',
      debug: '#7b1fa2'
    };
    
    return (
      <View style={styles.logItem}>
        <Text style={[styles.logText, { color: colors[item.type] }]}>
          [{item.timestamp.toLocaleTimeString()}] {item.message}
        </Text>
        {item.details && (
          <Text style={styles.logDetails}>
            {JSON.stringify(item.details, null, 2)}
          </Text>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Google Photos Migration</Text>

      {/* Debug Info */}
      <View style={styles.debugInfo}>
        <Text>XSRF Token: {xsrfToken ? '✅ Available' : '❌ Missing'}</Text>
        <Text>Cookies: {cookies ? '✅ Loaded' : '❌ Missing'}</Text>
      </View>

      {/* Main Interface */}
      {!xsrfToken ? (
        <Button
          title="Login to Google Photos"
          onPress={() => setShowWebView(true)}
        />
      ) : (
        <>
          <TextInput
            placeholder="Destination email"
            value={destinationEmail}
            onChangeText={setDestinationEmail}
            style={styles.input}
          />
          <Button
            title={isLoading ? "Loading..." : "Fetch Photos"}
            onPress={fetchPhotos}
            disabled={isLoading}
          />
        </>
      )}

      {/* Hidden WebView for auth */}
      <WebView
        ref={webviewRef}
        source={{ uri: 'https://photos.google.com' }}
        onMessage={handleWebViewMessage}
        injectedJavaScript={`
          window.ReactNativeWebView.postMessage({
            type: 'cookies',
            cookies: document.cookie
          });
          true;
        `}
        style={{ height: 1, opacity: 0.01 }}
      />

      {/* Debug Console */}
      <ScrollView style={styles.logContainer}>
        <Text style={styles.sectionHeader}>Debug Console</Text>
        <FlatList
          data={logs}
          renderItem={renderLogItem}
          keyExtractor={(item, index) => index.toString()}
        />
      </ScrollView>

      {/* Loading Indicator */}
      {(isLoading || isMigrating) && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" />
          <Text style={styles.loadingText}>
            {isMigrating ? 'Migrating...' : 'Loading...'}
          </Text>
        </View>
      )}
    </View>
  );
};

// Styles
const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#f5f5f5' },
  header: { fontSize: 22, fontWeight: 'bold', marginBottom: 16 },
  debugInfo: { 
    backgroundColor: '#fff', 
    padding: 12, 
    marginBottom: 16,
    borderRadius: 8
  },
  input: { 
    borderWidth: 1, 
    borderColor: '#ccc', 
    padding: 12, 
    marginBottom: 16,
    backgroundColor: '#fff',
    borderRadius: 8
  },
  logContainer: { 
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12
  },
  sectionHeader: {
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333'
  },
  logItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  logText: {
    fontSize: 12,
    fontFamily: 'monospace'
  },
  logDetails: {
    fontSize: 10,
    color: '#666',
    fontFamily: 'monospace'
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.8)'
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16
  }
});

export default App;
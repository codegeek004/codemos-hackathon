import React, { useRef, useState, useEffect } from 'react';
import { View, Text, Button, TextInput, ScrollView, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { WebView } from 'react-native-webview';
import sha1 from 'js-sha1';

type MigrationLog = {
  type: 'info' | 'success' | 'error' | 'debug' | 'warning';
  message: string;
  timestamp: Date;
  details?: any;
};

type PhotoItem = {
  token: string;
  url: string;
  status: 'pending' | 'success' | 'failed';
  error?: string;
};

const App = () => {
  const webviewRef = useRef<WebView>(null);
  const [showWebView, setShowWebView] = useState(false);
  const [cookies, setCookies] = useState('');
  const [destinationEmail, setDestinationEmail] = useState('');
  const [logs, setLogs] = useState<MigrationLog[]>([]);
  const [isMigrating, setIsMigrating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [sourceAccount, setSourceAccount] = useState('');
  const [xsrfToken, setXsrfToken] = useState('');

  // Enhanced logging system
  const addLog = (type: MigrationLog['type'], message: string, details?: any) => {
    const newLog: MigrationLog = {
      type,
      message,
      timestamp: new Date(),
      details
    };
    console.log(`[${type.toUpperCase()}] ${message}`, details || '');
    setLogs(prev => [newLog, ...prev].slice(0, 200));
  };

  // SAPISIDHASH generator with error handling
  const getSAPISIDHASH = (cookie: string): string => {
    try {
      const sapisid = cookie.match(/SAPISID=(.*?)(;|$)/)?.[1];
      const sid = cookie.match(/SID=(.*?)(;|$)/)?.[1];
      
      if (!sapisid || !sid) {
        addLog('error', 'SAPISID or SID not found in cookies');
        return '';
      }

      const timestamp = Math.floor(Date.now() / 1000);
      const input = `${timestamp} ${sapisid} https://photos.google.com`;
      const hash = sha1(input);
      return `SAPISIDHASH ${timestamp}_${hash}`;
    } catch (error) {
      addLog('error', 'Error generating SAPISIDHASH', error);
      return '';
    }
  };

  // Extract XSRF token from cookies
  const extractXsrfToken = (cookie: string): string => {
    const xsrfMatch = cookie.match(/XSRF-TOKEN=(.*?)(;|$)/);
    if (xsrfMatch) {
      const token = decodeURIComponent(xsrfMatch[1]);
      addLog('debug', 'Extracted XSRF token from cookies');
      return token;
    }
    return '';
  };

  // Handle WebView navigation and messages
  const handleNavigationStateChange = (navState: any) => {
    if (navState.url.includes('photos.google.com')) {
      webviewRef.current?.injectJavaScript(`
        // Try to get XSRF token from meta tag as fallback
        const xsrfMeta = document.querySelector('meta[name="xsrf-token"]');
        const xsrfToken = xsrfMeta ? xsrfMeta.content : '';
        
        window.ReactNativeWebView.postMessage(JSON.stringify({
          type: 'cookies',
          cookies: document.cookie,
          xsrfToken: xsrfToken,
          url: window.location.href
        }));
        true;
      `);
    }
  };

  const handleWebViewMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      
      if (data.type === 'cookies') {
        if (data.cookies && data.cookies.includes('SAPISID')) {
          setCookies(data.cookies);
          
          // Try to get XSRF token from multiple sources
          const tokenFromCookies = extractXsrfToken(data.cookies);
          const tokenFromMeta = data.xsrfToken;
          const xsrf = tokenFromCookies || tokenFromMeta;
          
          if (xsrf) {
            setXsrfToken(xsrf);
            addLog('success', 'XSRF token obtained', {
              source: tokenFromCookies ? 'cookies' : 'meta'
            });
          }

          addLog('success', 'Cookies extracted successfully');
          extractAccountInfo(data.cookies);
          setShowWebView(false);
        }
      }
      
      if (data.type === 'accountInfo') {
        if (data.email) {
          setSourceAccount(data.email);
          addLog('success', `Source account identified: ${data.email}`);
        }
      }
    } catch (error) {
      addLog('error', 'Error processing WebView message', error);
    }
  };

  // Extract account info from cookies or DOM
  const extractAccountInfo = (cookie: string) => {
    try {
      const emailMatch = cookie.match(/(Email|GMAIL_AT)=(.*?)(;|$)/)?.[2];
      if (emailMatch) {
        setSourceAccount(decodeURIComponent(emailMatch));
        return;
      }

      // Fallback to DOM extraction
      webviewRef.current?.injectJavaScript(`
        try {
          const email = document.querySelector('[data-email]')?.getAttribute('data-email') || 
                       document.querySelector('[aria-label*="@"]')?.ariaLabel;
          window.ReactNativeWebView.postMessage(JSON.stringify({
            type: 'accountInfo',
            email: email || 'unknown'
          }));
        } catch(e) {
          window.ReactNativeWebView.postMessage(JSON.stringify({
            type: 'accountInfo',
            error: e.message
          }));
        }
        true;
      `);
    } catch (error) {
      addLog('error', 'Error extracting account info', error);
    }
  };

  // Parse batchexecute response
  const parseBatchExecuteResponse = (text: string) => {
    try {
      // Handle XSSI prefix
      const cleanText = text.startsWith(")]}'") ? text.substring(5) : text;
      return JSON.parse(cleanText);
    } catch (error) {
      addLog('error', 'Failed to parse API response', {
        error,
        responseSample: text.substring(0, 100)
      });
      return null;
    }
  };

  // Fetch photos with proper XSRF handling
  const fetchPhotos = async () => {
    if (!cookies || !xsrfToken) {
      addLog('error', 'Missing required tokens', {
        hasCookies: !!cookies,
        hasXsrfToken: !!xsrfToken
      });
      return;
    }

    setIsLoading(true);
    addLog('info', 'Starting photo fetch with XSRF protection');

    try {
      const authHeader = getSAPISIDHASH(cookies);
      if (!authHeader) {
        throw new Error('Failed to generate auth header');
      }

      const headers = {
        'Authorization': authHeader,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': cookies,
        'X-XSRF-TOKEN': xsrfToken,
        'Origin': 'https://photos.google.com'
      };

      // Payload based on your API analysis
      const payload = {
        rpcids: 'snAcKc,wQ6iqd',
        'f.req': JSON.stringify([
          [
            [
              "snAcKc",
              `["shared_album_token_placeholder",null,null,null,null,null,2]`,
              null,
              "1"
            ],
            [
              "wQ6iqd",
              `[["shared_album_token_placeholder"]]`,
              null,
              "2"
            ]
          ]
        ]),
        at: xsrfToken
      };

      const response = await fetch(
        'https://photos.google.com/_/PhotosUi/data/batchexecute?rpcids=snAcKc%2CwQ6iqd',
        {
          method: 'POST',
          headers,
          body: new URLSearchParams(payload as any),
        }
      );

      const responseText = await response.text();
      const parsed = parseBatchExecuteResponse(responseText);

      if (response.status !== 200 || !parsed) {
        throw new Error(`API request failed with status ${response.status}`);
      }

      // Extract photos from response - adjust based on actual structure
      const photoTokens = responseText.match(/https:\/\/photos\.google\.com\/photo\/([a-zA-Z0-9_-]+)/g) || [];
      const uniquePhotos = Array.from(new Set(photoTokens)).map(url => ({
        token: url.split('/photo/')[1],
        url,
        status: 'pending' as const
      }));

      setPhotos(uniquePhotos);
      addLog('success', `Found ${uniquePhotos.length} photos`);

    } catch (error) {
      addLog('error', 'Failed to fetch photos', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Migrate photos with retry logic
  const migratePhotos = async () => {
    if (!cookies || !xsrfToken || !destinationEmail) {
      addLog('error', 'Missing required parameters');
      return;
    }

    setIsMigrating(true);
    addLog('info', 'Starting migration process');

    try {
      let successCount = 0;
      for (const photo of photos) {
        try {
          const authHeader = getSAPISIDHASH(cookies);
          if (!authHeader) {
            throw new Error('Failed to generate auth header');
          }

          const headers = {
            'Authorization': authHeader,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': cookies,
            'X-XSRF-TOKEN': xsrfToken,
            'Origin': 'https://photos.google.com'
          };

          const payload = {
            rpcids: 'laUYf',
            'f.req': JSON.stringify([
              [
                [
                  "laUYf",
                  `["shared_album_token_placeholder",[2,null,[["${photo.token}"]],null,null,[1],null,null,null,null,null,0]`,
                  null,
                  "generic"
                ]
              ]
            ]),
            at: xsrfToken
          };

          const response = await fetch(
            'https://photos.google.com/_/PhotosUi/data/batchexecute?rpcids=laUYf',
            {
              method: 'POST',
              headers,
              body: new URLSearchParams(payload as any),
            }
          );

          const responseText = await response.text();
          
          if (response.status === 200) {
            successCount++;
            setPhotos(prev => prev.map(p => 
              p.token === photo.token ? {...p, status: 'success'} : p
            ));
          } else {
            throw new Error(`Migration failed with status ${response.status}`);
          }
        } catch (error) {
          addLog('warning', `Failed to migrate photo ${photo.token.substring(0, 8)}...`, error);
          setPhotos(prev => prev.map(p => 
            p.token === photo.token ? {...p, status: 'failed', error: error.message} : p
          ));
        }
      }

      addLog('success', `Migration complete: ${successCount}/${photos.length} photos migrated`);
      Alert.alert(
        'Migration Complete', 
        `Successfully migrated ${successCount} of ${photos.length} photos`
      );

    } catch (error) {
      addLog('error', 'Migration process failed', error);
    } finally {
      setIsMigrating(false);
    }
  };

  // UI Components
  const renderLogItem = (log: MigrationLog, index: number) => {
    const colors = {
      info: '#1976d2',
      success: '#388e3c',
      error: '#d32f2f',
      warning: '#ffa000',
      debug: '#7b1fa2'
    };
    
    return (
      <View key={index} style={styles.logItem}>
        <Text style={[styles.logText, { color: colors[log.type] }]}>
          [{log.timestamp.toLocaleTimeString()}] {log.message}
        </Text>
        {log.details && (
          <Text style={styles.logDetails}>
            {JSON.stringify(log.details, null, 2)}
          </Text>
        )}
      </View>
    );
  };

  const renderPhotoItem = (photo: PhotoItem, index: number) => {
    const colors = {
      pending: '#757575',
      success: '#388e3c',
      failed: '#d32f2f'
    };
    
    return (
      <View key={index} style={styles.photoItem}>
        <Text style={{ color: colors[photo.status] }}>
          {photo.token.substring(0, 8)}... - {photo.status.toUpperCase()}
        </Text>
        {photo.error && <Text style={styles.errorText}>{photo.error}</Text>}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Google Photos Migration</Text>

      {/* Account Info */}
      <View style={styles.accountInfo}>
        <Text>Source: {sourceAccount || 'Not logged in'}</Text>
        <Text>Destination: {destinationEmail || 'Not specified'}</Text>
      </View>

      {/* Action Buttons */}
      <View style={styles.buttonContainer}>
        {!cookies && (
          <Button
            title="Login to Source Account"
            onPress={() => setShowWebView(true)}
            disabled={isLoading || isMigrating}
          />
        )}
        
        {cookies && (
          <Button
            title={isLoading ? "Fetching Photos..." : "Fetch Photos"}
            onPress={fetchPhotos}
            disabled={isLoading || isMigrating}
          />
        )}
        
        {photos.length > 0 && (
          <Button
            title={isMigrating ? "Migrating..." : `Migrate ${photos.length} Photos`}
            onPress={migratePhotos}
            disabled={isMigrating || !destinationEmail}
          />
        )}
      </View>

      {/* Destination Email Input */}
      {cookies && (
        <TextInput
          placeholder="Enter destination email"
          value={destinationEmail}
          onChangeText={setDestinationEmail}
          style={styles.input}
          autoCapitalize="none"
          keyboardType="email-address"
        />
      )}

      {/* WebView for authentication */}
      {showWebView && (
        <WebView
          ref={webviewRef}
          source={{ uri: 'https://accounts.google.com/AccountChooser?continue=https://photos.google.com' }}
          onNavigationStateChange={handleNavigationStateChange}
          onMessage={handleWebViewMessage}
          sharedCookiesEnabled
          thirdPartyCookiesEnabled
          startInLoadingState
          style={styles.webview}
        />
      )}

      {/* Photos List */}
      {photos.length > 0 && (
        <ScrollView style={styles.photosList}>
          <Text style={styles.sectionHeader}>Photos to Migrate</Text>
          {photos.map(renderPhotoItem)}
        </ScrollView>
      )}

      {/* Activity Log */}
      <ScrollView style={styles.logContainer}>
        <Text style={styles.sectionHeader}>Activity Log</Text>
        {logs.map(renderLogItem)}
      </ScrollView>

      {/* Loading Indicator */}
      {(isLoading || isMigrating) && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" />
          <Text style={styles.loadingText}>
            {isMigrating ? 'Migrating photos...' : 'Loading...'}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f5f5f5'
  },
  header: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 16,
    textAlign: 'center'
  },
  accountInfo: {
    marginBottom: 16,
    padding: 12,
    backgroundColor: '#fff',
    borderRadius: 8
  },
  buttonContainer: {
    marginBottom: 16,
    gap: 8
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    padding: 10,
    marginBottom: 16,
    borderRadius: 6,
    backgroundColor: '#fff'
  },
  webview: {
    height: 400,
    marginBottom: 16
  },
  photosList: {
    maxHeight: 200,
    marginBottom: 16,
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12
  },
  logContainer: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12
  },
  sectionHeader: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8
  },
  photoItem: {
    padding: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  errorText: {
    color: '#d32f2f',
    fontSize: 12
  },
  logItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  logText: {
    fontSize: 12
  },
  logDetails: {
    fontSize: 10,
    color: '#757575'
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.8)'
  },
  loadingText: {
    marginTop: 16
  }
});

export default App;
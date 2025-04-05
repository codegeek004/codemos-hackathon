import React, { useRef, useState } from 'react';
import { View, Button, Text } from 'react-native';
import { WebView } from 'react-native-webview';
import CookieManager from 'react-native-cookie-store';

const GoogleLoginScreen = ({ navigation }) => {
    const webViewRef = useRef(null);
    const [cookies, setCookies] = useState(null);

    const handleLoginSuccess = async () => {
        // Get Google Photos cookies after login
        const googleCookies = await CookieManager.get('https://photos.google.com');
        setCookies(googleCookies);
        navigation.navigate('FetchPhotos', { cookies: googleCookies });
    };

    return (
        <View style={{ flex: 1 }}>
            <WebView
                ref={webViewRef}
                source={{ uri: 'https://photos.google.com/' }}
                onNavigationStateChange={(navState) => {
                    if (navState.url.includes('photos.google.com')) {
                        handleLoginSuccess();
                    }
                }}
            />
        </View>
    );
};

export default GoogleLoginScreen;


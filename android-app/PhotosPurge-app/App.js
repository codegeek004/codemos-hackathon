import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import GoogleLoginScreen from './GoogleLoginScreen';
import FetchPhotosScreen from './FetchPhotosScreen';

const Stack = createStackNavigator();

const App = () => {
    return (
        <NavigationContainer>
            <Stack.Navigator initialRouteName="Login">
                <Stack.Screen name="Login" component={GoogleLoginScreen} />
                <Stack.Screen name="FetchPhotos" component={FetchPhotosScreen} />
            </Stack.Navigator>
        </NavigationContainer>
    );
};

export default App;


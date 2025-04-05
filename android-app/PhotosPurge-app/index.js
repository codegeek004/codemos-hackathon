import { AppRegistry } from 'react-native';
import App from './App'; // 👈 This should point to your main App component
import { name as appName } from './app.json';

AppRegistry.registerComponent(appName, () => App);


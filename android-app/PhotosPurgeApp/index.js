import { AppRegistry } from 'react-native';
import App from './App'; // <- your main component
import { name as appName } from './app.json';

AppRegistry.registerComponent(appName, () => App);
export default function MainApp() {
  return <AuthScreen />;
}

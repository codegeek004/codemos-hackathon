import React, { useState } from 'react';
import { View, Text, Button, StyleSheet, Alert } from 'react-native';
import * as WebBrowser from 'expo-web-browser';

export default function App() {
  const [destinationAccount, setDestinationAccount] = useState(null);

  const handleMigratePress = async () => {
    if (!destinationAccount) {
      Alert.alert(
        'Select Destination Account',
        'Please choose a Google account to migrate the photos to.',
        [
          {
            text: 'Choose Account',
            onPress: async () => {
              const result = await WebBrowser.openBrowserAsync(
                'https://accounts.google.com/AddSession'
              );
              // NOTE: You won't get account info directly here in Expo Go.
              // In production (standalone app), you'll extract cookies here.
              Alert.alert('Manual Step', 'Now you can copy cookies for migration.');
            }
          }
        ]
      );
    } else {
      // Trigger the migration logic here (using extracted cookies/token)
      Alert.alert('Migration Started', `Migrating photos to: ${destinationAccount}`);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Photo Migrator</Text>
      <Button title="Migrate All Photos" onPress={handleMigratePress} />
      {destinationAccount && (
        <Text style={styles.info}>Destination: {destinationAccount}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f2f2f2',
    padding: 20,
  },
  title: {
    fontSize: 24,
    marginBottom: 20,
  },
  info: {
    marginTop: 10,
    fontSize: 16,
    color: '#555',
  },
});


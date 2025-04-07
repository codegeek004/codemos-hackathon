import React, { useEffect } from 'react';
import { View, Text, ActivityIndicator } from 'react-native';

export default function MigrationScreen({ route }) {
  const { cookies, destinationEmail } = route.params;

  useEffect(() => {
    const migratePhotos = async () => {
      // Your batchexecute reverse-engineered logic goes here
      console.log('Cookies:', cookies);
      console.log('Destination:', destinationEmail);
    };

    migratePhotos();
  }, []);

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Migrating photos...</Text>
      <ActivityIndicator size="large" />
    </View>
  );
}


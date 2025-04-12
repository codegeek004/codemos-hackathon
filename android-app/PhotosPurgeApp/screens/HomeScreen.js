import React from 'react';
import { View, Text, Button } from 'react-native';

export default function HomeScreen({ navigation, route }) {
  const { cookies } = route.params;

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Welcome to Photo Migrator</Text>
      <Button
        title="Migrate All Photos"
        onPress={() =>
          navigation.navigate('SelectAccount', { cookies })
        }
      />
    </View>
  );
}

